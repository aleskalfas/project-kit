#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — move-issue (verb-subject per DEC-020).

Transitions a GitHub issue through the lifecycle state machine declared
in `workflow.yaml`, which since DEC-033 is a process definition bound to
the shared process substrate (COR-033) — a KEYED process (COR-032), one
journey per issue number.

State-machine mechanics (position resolution + the move journal) are
DELEGATED to the process engine via `pkit process …` (subprocess, never
imported, ADR-020): this script reads the issue's position from the
engine and, after applying its domain side-effect, journals the move
through the engine (the seam-ordering contract in .pkit/process/
README.md). The engine's detection — the lifecycle's classifier,
`detect-state` — reproduces this script's inference precedence, so
position is identical (behaviour parity is the acceptance bar). The
parity-critical wrapper-side concerns STAY here: membership, placeholder,
authorisation/bypass/TTY, and the forward cascade.

The substrate-specific mechanics differ per adopter config. WHICH substrate
carries `state` is asked of `_lib/axis_carriage` — the map governs the axis
where it binds it, and `has_projects_v2_board` governs only where the map is
silent (per [project-management:DEC-051-axis-carriage-activation]):

  * `board` — the Projects v2 single-select `Status` field carries the state.
    State changes go through `gh project item-edit` (deferred at v1 —
    surfaces as a dry-run guidance message until kit issue #122 lands).
  * `kit-label` / `adopter-label` — the state lives as a label: the kit's
    `state:*` in greenfield, or the adopter's own label under a `label:`
    binding. State changes happen via `gh issue edit --add-label <new>
    --remove-label <old>`, both resolved through the seam.
  * `derived` / `degrade` — no label is written or removed (a derived state is
    carried by open/closed, and a degraded one by nothing); the wrapper's other
    domain side-effects still fire.

The forward cascade per DEC-006 fires upward on a forward move: the
script walks from the issue to the top of its hierarchy, one parent at a
time through the parent each first line names (`_lib/body_parent_ref`),
and brings each ancestor that is behind up to the issue's state, capped
at in-progress, through declared transitions only — an ancestor in todo
goes to backlog, then to in-progress, each step its own label write,
journaled where a journal is kept with the issue's move as the reason.
A move to done from todo or backlog (won't-do) moves no ancestor. The
cascade is not an authorisation: it asks for no confirmation, posts no audit
comment and fires no hook. At the `full` audit projection each ancestor it
moves gets the provenance comment a governed move gets, naming the move that
caused it. It runs on the no-op path too, so running a
move again finishes a cascade a failure left incomplete — for a move to
done, once the issue has closed as completed — and it does not run where
the state is not written as a label. See the "forward cascade" section
near the end of this file.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/move-issue.py 42 --to in-progress

Or via the dispatcher (per COR-021):
  pkit project-management move-issue 42 --to in-progress

Exit codes:
  0  transitioned, already there, or dry-run reported — a forward cascade
     left incomplete is a warning, not a failure: the issue's move stands
  1  membership refusal / authorisation refusal
  2  usage error (unknown state, illegal transition, issue not found)
  3  gh failure
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import audit as _audit
from _lib import (
    axis_carriage,
    axis_labels,
    body_parent_ref,
    bootstrap_gate,
    composed_move,
    containment,
    engine_said,
    move_journal,
    session_guard,
    state_timeline,
)
from _lib import lifecycle_inference as infer

# The one fetch / scan / post-once wiring every audit writer shares (#902).
from _lib.comment import post_audit_once
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.hooks import fire_hooks
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.move_journal import PROCESS_ADDRESS
from _lib.placeholder_detection import (
    PHASE_TRANSITION,
    detect_placeholder_residuals,
)
from _lib.structural_type import infer_structural_type

SEVERITY_HARD_REJECT = "hard-reject"
SEVERITY_WARNING = "warning"

# The DEC-049 audit primitives — the canonical marker, the schema-sourced
# template, the renderer and the projection knob — live ONCE in `_lib.audit`,
# shared with every other audit-comment writer (COR-007). Re-exported under the
# module-private names this script's call sites and tests already use, so the
# extraction moved the implementation without moving the call surface.
SEVERITY_BYPASSABLE = _audit.SEVERITY_BYPASSABLE
_AUDIT_MARKER = _audit.AUDIT_MARKER
_AUDIT_TEMPLATE_FALLBACK = _audit.AUDIT_TEMPLATE_FALLBACK
_load_audit_template = _audit.load_audit_template
_render_audit_comment = _audit.render_audit_comment
_audit_projection = _audit.audit_projection

# The idempotency key that closes a TRANSITION audit comment (#901). It is a key,
# not a kind marker: the comment's kind is still the template's `<!-- pkit-audit -->`
# on its first line, and this trailing line only lets a retry recognise the
# comment it already posted. Built by `_transition_audit_key` through the shared
# `_lib.audit.audit_key`; a retry skips only when a comment with the exact body
# was posted, unedited, by the account `gh` posts as (`_lib.comment.
# post_audit_once`, #902).
TRANSITION_AUDIT_WRITER = "move-issue"
TRANSITION_AUDIT_KEY_PREFIX = f"{_audit.AUDIT_KEY_PREFIX}{TRANSITION_AUDIT_WRITER}:"


@functools.cache
def _pkit_version() -> str:
    """Best-effort pkit version for a `full`-projection provenance stamp, read
    once per run however many comments carry it."""
    try:
        proc = subprocess.run(
            ["pkit", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    parts = proc.stdout.strip().replace(",", " ").split()
    return parts[-1] if parts else ""


def _render_provenance_comment(
    invoker, from_state, *to_states: str, cause: str | None = None
) -> str:
    """DEC-049 `full` projection: a provenance-stamped record of a governed move,
    carrying the pkit version — the governed-vs-ungoverned boundary made visible on
    the issue. Absence of such a comment beside a timeline label change flags an
    out-of-band mutation.

    A move through several states names each (`todo → backlog → in-progress`), and
    a move another move caused — a forward-cascaded one — names that ``cause`` on a
    line of its own, as its journal entry's reason does."""
    actor = getattr(invoker, "github_login", None) or getattr(invoker, "email", None) or "unknown"
    version = _pkit_version()
    stamp = f" — pkit {version}" if version else ""
    move = " → ".join(state for state in (from_state, *to_states) if state)
    comment = f"{_AUDIT_MARKER}\n{actor} moved {move} (governed by pkit){stamp}"
    return f"{comment}\n{cause}" if cause else comment


@dataclass(frozen=True)
class Transition:
    """One transition entry from workflow.yaml's `transitions:` list."""

    from_state: str
    to_state: str
    authorisation: str  # "user" | "agent-autonomous"
    severity: str  # "hard-reject" | "bypassable-with-audit" | "warning"
    applies_to: tuple[str, ...]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Move a GitHub issue to a target lifecycle state. Reads "
            "workflow.yaml; refuses unknown transitions; cascades parents "
            "per DEC-006."
        ),
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number to transition.",
    )
    parser.add_argument(
        "--to",
        required=True,
        help=("Target state: one of todo, backlog, in-progress, review, done."),
    )
    parser.add_argument(
        "--bypass",
        action="store_true",
        help=(
            "Bypass a bypassable-with-audit gate by posting an audit comment "
            "(per DEC-014). Required for transitions with that severity when "
            "authorisation = user."
        ),
    )
    parser.add_argument(
        "--bypass-reason",
        default=None,
        help=(
            "Reason recorded in the audit comment and, where a journal is kept, "
            "on the move's journal entry; required (non-empty) whenever --bypass "
            "is set — a bare --bypass is refused."
        ),
    )
    parser.add_argument(
        "--merged-pr",
        type=int,
        default=None,
        metavar="PR",
        help=(
            "With --to done only: the merged PR that completed the issue. Where "
            "a journal is kept, the move's entry gives it as the reason, worded "
            "as close-issue words it for the other issues a PR closes "
            "(`pr-merge close: closed by merged PR #<PR>`). done-work passes it."
        ),
    )
    parser.add_argument(
        "--no-cascade",
        action="store_true",
        help="Skip the forward cascade on the issue's ancestors.",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            f"(default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan; do not invoke gh.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    if args.merged_pr is not None and args.to != "done":
        print(
            f"error: --merged-pr applies to --to done only (got --to {args.to}).",
            file=sys.stderr,
        )
        return 2

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            f"error: {CAPABILITY_NAME} capability not found.",
            file=sys.stderr,
        )
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("move-issue", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")

    config = load_adopter_config(capability_root)

    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before any gh
    # mutation: target repo (cwd) vs session anchor (CLAUDE_PROJECT_DIR).
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    workflow = _read_yaml(capability_root / "schemas" / "workflow.yaml", yaml_loader)
    issue_types = _read_yaml(capability_root / "schemas" / "issue-types.yaml", yaml_loader)
    classification = _read_yaml(capability_root / "schemas" / "classification.yaml", yaml_loader)
    body_format = _read_yaml(capability_root / "schemas" / "body-format.yaml", yaml_loader)
    config = _read_yaml(capability_root / "project" / "config.yaml", yaml_loader)

    # Validate the target state.
    state_ids = _known_states(workflow)
    if args.to not in state_ids:
        print(
            f"error: unknown target state {args.to!r}. "
            f"Known states: {', '.join(sorted(state_ids))}.",
            file=sys.stderr,
        )
        return 2

    # Fetch current issue + state inference.
    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    title = str(issue.get("title", ""))
    body = str(issue.get("body") or "")
    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    state = str(issue.get("state", "")).lower()
    milestone = issue.get("milestone") or {}
    closed_as = _close_reason(issue)
    # The reason the move to done is journaled with when a merged PR made it
    # (`--merged-pr`): an issue already closed is one the merge closed.
    merge_reason = (
        move_journal.pr_merge_close_reason(args.merged_pr, closed_by_merge=state == "closed")
        if args.merged_pr is not None
        else None
    )

    structural_type = infer_structural_type(
        title, issue_types, classification=classification, labels=labels
    )
    if structural_type is None:
        # Unrecoverable: no [Type] title prefix AND no `type:*` kind label to
        # fall back on. A Task always carries a `type:*` label (so it recovers
        # even with the prefix edited away); a container (EPIC/Feature/Umbrella)
        # has no distinguishing `type:*` label, so an edited-away container
        # prefix lands here — surfaced as malformed, never silently guessed.
        print(
            f"error: cannot determine structural type for issue "
            f"#{args.issue_number}: title {title!r} matches no known [Type] "
            "prefix and no `type:*` kind label is present to recover a Task "
            "from.\n"
            "  → Restore the issue's title prefix (e.g. [EPIC]/[Feature]/"
            "[Umbrella]/[Task]) so the structural type can be determined.",
            file=sys.stderr,
        )
        return 2

    # The adopter's optional substrate-map (ADR-026): None ⇒ greenfield (state
    # is a `state:*` label); a present map may bind state to a `derive`
    # predicate ⇒ no kit state label is written (the open/closed substrate
    # carries it). Loaded once and threaded through both position inference and
    # every plan computation. Loaded BEFORE the position read so the local
    # fallback below is map-aware (agrees with the engine's map-aware detection).
    substrate_map = axis_labels.load_substrate_map(capability_root)

    # Position: read from the engine (DEC-033 D5 — read, don't re-infer). The
    # engine's detection — the lifecycle's classifier — reproduces this script's
    # inference precedence (and is map-aware, ADR-026 §5), so the result is
    # identical; fall back to the local inference when the engine is unreachable
    # (e.g. `pkit` not on PATH) or cannot tell where the issue is (an
    # indeterminate position), so a move is never blocked. The fallback is
    # threaded the same map so it agrees with the engine under a present derive
    # binding.
    engine_status = _engine_status(args.issue_number)
    current_state = _position_from_status(engine_status)
    if current_state is None:
        current_state = _infer_current_state(
            state=state, milestone=milestone, labels=labels, substrate_map=substrate_map
        )

    # WHICH substrate carries `state` — one question, one answer, asked of the
    # accessor ([project-management:DEC-051-axis-carriage-activation] decision
    # point 4). Every branch below that used to read `has_projects_v2_board`
    # reads this instead: under a map that binds `state` to the adopter's own
    # labels, a configured board no longer suppresses the label write, and under
    # a `derive` binding the label planner already writes nothing.
    state_on_board = axis_carriage.is_board_carried("state", config, substrate_map)

    # Audit-comment projection (DEC-049): where the project keeps a journal it
    # records every move regardless; `audit.projection` controls the GitHub
    # comment projection — `off` posts nothing, `audit` (default) posts only
    # override justifications, `full` posts a provenance-stamped comment for
    # every governed move, a forward-cascaded one included.
    projection = _audit_projection(config)

    # What the forward cascade (DEC-006) reads and writes with, for either path.
    cascade_context = _CascadeContext(
        workflow=workflow,
        issue_types=issue_types,
        classification=classification,
        config=config,
        substrate_map=substrate_map,
        invoker=invoker,
        projection=projection,
        levels=_cascade_levels(workflow),
    )

    def moved_issue(origin: str | None) -> _MovedIssue:
        """This issue as the forward cascade reads it, moved from ``origin``."""
        return _MovedIssue(
            number=args.issue_number,
            body=body,
            structural_type=structural_type,
            origin=origin,
            target=args.to,
            closed=state == "closed",
            closed_as=closed_as,
        )

    # Idempotency check: issue is already at the requested state.
    #
    # Must run BEFORE the transition-table lookup so that callers (e.g.
    # done-work after a squash-merge whose `Closes #N` auto-closes the
    # issue) don't get a spurious "done → done" error. On the label
    # substrate the state:* label may be stale (e.g. state:review
    # lingering after a GitHub-native close), so we reconcile it here
    # rather than returning immediately without touching the label.
    if args.to == current_state:
        print(f"move-issue: #{args.issue_number}")
        print(f"  title:        {title}")
        print(f"  type:         {structural_type}")
        print(f"  current:      {current_state}")
        print(f"  target:       {args.to}")
        print("\n[noop] already at target state; reconciling labels if needed.")
        if not args.no_cascade:
            print(
                "  Any ancestor behind it is still brought level, with no prompt: "
                "the forward cascade asks for none."
            )
        if not args.dry_run and not state_on_board:
            plan = _compute_plan(
                issue_number=args.issue_number,
                current_state=current_state,
                target_state=args.to,
                state_on_board=False,
                labels=labels,
                substrate_map=substrate_map,
            )
            # Only act when there is a stale label to remove (the add is
            # idempotent but skip the gh round-trip if nothing to fix).
            if plan.remove_label:
                print(f"  reconcile: removing stale label {plan.remove_label!r}")
                if not _gh_apply_state_label(args.issue_number, plan, config):
                    return 3
                if state == "closed" and not _journal_logging_off(engine_status):
                    _journal_closed_issue_relabel(
                        args.issue_number,
                        args.to,
                        workflow=workflow,
                        structural_type=structural_type,
                        milestone=milestone,
                        labels=labels,
                        substrate_map=substrate_map,
                        actor=invoker.github_login,
                        reason=merge_reason,
                    )
        # The forward cascade is idempotent, so the issue already being in place
        # does not end the walk: re-running a move whose cascade left an ancestor
        # behind brings that ancestor level. An issue already at done came there
        # from where its old label places it — a merge's close leaves review —
        # which tells a finished issue from a won't-do one; where the label
        # already reads done, its close reason tells them apart instead.
        if not args.no_cascade:
            origin = (
                infer.state_before_close(
                    milestone=milestone, labels=labels, substrate_map=substrate_map
                )
                if args.to == "done"
                else None
            )
            cascade = _preview_forward_cascade(moved_issue(origin), cascade_context)
            if cascade is not None and args.dry_run:
                print("\n[dry-run] nothing written.")
            elif cascade is not None:
                _run_forward_cascade(cascade, cascade_context)
        return 0

    # Look up the transition.
    transition = _find_transition(workflow, current_state, args.to, structural_type)
    if transition is None:
        legal_targets = _legal_targets(workflow, current_state, structural_type)
        print(
            f"error: no transition {current_state!r} → {args.to!r} "
            f"declared in workflow.yaml for {structural_type!r}.\n"
            f"  legal targets from {current_state!r}: "
            f"{', '.join(legal_targets) if legal_targets else '<none>'}",
            file=sys.stderr,
        )
        return 2

    # Authorisation gate.
    if transition.authorisation == "user":
        if transition.severity == SEVERITY_HARD_REJECT:
            # User-gated hard-reject: requires --yes from the caller as the
            # explicit authorisation signal (no bypass possible).
            if not args.yes and sys.stdin.isatty():
                pass  # fall through to confirm prompt below
            elif not args.yes:
                print(
                    f"[refused] transition {current_state!r} → {args.to!r} is "
                    f"user-authorised (hard-reject on violation).\n"
                    "          → Pass --yes to confirm the authorisation, "
                    "or re-run from an interactive shell.",
                    file=sys.stderr,
                )
                return 1
        elif transition.severity == SEVERITY_BYPASSABLE:
            # Bypassable: caller must pass --bypass + --bypass-reason or
            # provide TTY confirmation.
            if not args.bypass and not (args.yes or sys.stdin.isatty()):
                print(
                    f"[refused] transition {current_state!r} → {args.to!r} is "
                    "bypassable-with-audit; pass --bypass --bypass-reason '...' "
                    "to record the audit comment, or run from a TTY.",
                    file=sys.stderr,
                )
                return 1
            # A --bypass override must carry a non-empty reason. The
            # bypassable-with-audit gate (DEC-014) records the reason in the
            # audit comment, and the override-flag convention (DEC-046)
            # requires it — a bare --bypass must refuse, not substitute a
            # placeholder. Refuse before any mutation or audit comment.
            if _bypass_reason_missing(args.bypass, args.bypass_reason):
                print(
                    f"[refused] transition {current_state!r} → {args.to!r}: "
                    "--bypass requires a non-empty --bypass-reason "
                    "(the audit comment records the reason per DEC-014 / "
                    "DEC-046).",
                    file=sys.stderr,
                )
                return 1

    # Residual-placeholder check per DEC-031 — hard-reject at transition.
    # Run before any mutation so an unauthored body blocks the transition.
    placeholder_findings = detect_placeholder_residuals(
        body=body,
        structural_type=structural_type,
        body_format=body_format,
        capability_root=capability_root,
        phase=PHASE_TRANSITION,
    )
    hard_reject_findings = [f for f in placeholder_findings if f[0] == "hard-reject"]
    if hard_reject_findings:
        print(
            f"[hard-reject] transition {current_state!r} → {args.to!r} blocked: "
            f"issue #{args.issue_number} body has not been authored.",
            file=sys.stderr,
        )
        for sev, label, detail in hard_reject_findings:
            print(f"  [{sev}] {label}: {detail}", file=sys.stderr)
        print(
            "  → Fill in the required sections of the issue body before advancing.",
            file=sys.stderr,
        )
        return 1

    print(f"move-issue: #{args.issue_number}")
    print(f"  title:        {title}")
    print(f"  type:         {structural_type}")
    print(f"  current:      {current_state}")
    print(f"  target:       {args.to}")
    print(f"  authorisation: {transition.authorisation}")
    print(f"  severity:      {transition.severity}")

    if state_on_board:
        print(
            f"\n[note] board substrate detected (projects_v2_board_id="
            f"{config.get('projects_v2_board_id')}). State lives on the "
            "Projects v2 Status field; bulk gh-project field-set is deferred "
            "(per DEC-019). This invocation will surface the planned move "
            "but not mutate the board field at v1."
        )

    plan = _compute_plan(
        issue_number=args.issue_number,
        current_state=current_state,
        target_state=args.to,
        state_on_board=state_on_board,
        labels=labels,
        substrate_map=substrate_map,
    )
    _print_plan(plan)

    # Cascade preview: each ancestor's steps, read before anything is written.
    cascade = None
    if not args.no_cascade and _is_forward(workflow, current_state, args.to):
        cascade = _preview_forward_cascade(moved_issue(current_state), cascade_context)

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    is_bypass_audit = (
        transition.authorisation == "user"
        and transition.severity == SEVERITY_BYPASSABLE
        and args.bypass
    )
    # The justification a bypassed gate was overridden with. Non-empty on a
    # bypass: the bypassable authorisation gate above refuses a --bypass without
    # a non-empty --bypass-reason. Empty when no gate was bypassed.
    bypass_reason = (args.bypass_reason or "").strip() if is_bypass_audit else ""
    if projection != "off" and is_bypass_audit:
        # move-issue is the sole writer of the TRANSITION audit comment (DEC-049): it renders the
        # one canonical comment from the schema template; wrappers pass the reason
        # through rather than posting their own (killing the #672 double-post).
        #
        # Posted BEFORE the mutation so the justification survives a failed
        # label write (DEC-049's `audit` floor), and posted exactly once per
        # mutation: a retry of that failed attempt finds its own comment by the
        # idempotency key and skips (#901), while the same transition made again
        # later has a grown landed-move count and posts its own (#954).
        key = _transition_audit_key(
            current_state,
            args.to,
            bypass_reason,
            _landed_moves(args.issue_number, engine_status, config, substrate_map),
        )
        audit_comment = (
            _render_audit_comment(capability_root, invoker, bypass_reason) + "\n\n" + key
        )
        if not _post_transition_audit_once(args.issue_number, audit_comment, key, config):
            return 3

    # Execute.
    if state_on_board:
        # Deferred: at v1 we only narrate the planned change for board
        # adopters. The label removal/add path is the operational one.
        print(
            "\n[ok] (board adopter) plan recorded; manual board edit may be "
            "required. Label substrate would be: see plan above."
        )
    else:
        ok = _gh_apply_state_label(args.issue_number, plan, config)
        if not ok:
            return 3

    # Seam-ordering (DEC-033 / process README): the domain side-effect (the
    # label/board edit) is applied above; now journal the move via the engine,
    # from the position read before it. Best-effort — a refusal or missing
    # `pkit` never fails the move, since live detection stays authoritative.
    #
    # `--actor` is the resolved GitHub login of the invoker (not the
    # authorisation token), so the engine's cross-authority gate compares
    # like-with-like against an artifact's `produced_by` login (COR-033 P4).
    # A bypassed move carries its justification as the entry's reason, at every
    # projection: the journal is the canonical trail where it is kept (DEC-049).
    # A move to done a merged PR made (`--merged-pr`) carries that PR's reason.
    # No move into done is bypassable in the shipped workflow, so at most one of
    # the two is given; were both, the bypass's justification is the entry's why.
    _journal_move(
        args.issue_number,
        current_state,
        args.to,
        invoker.github_login,
        reason=_bypass_journal_reason(bypass_reason) or merge_reason,
    )

    # DEC-049 `full` projection: post a provenance-stamped comment for a governed
    # move not already covered by the bypass audit above, so the governed-vs-
    # ungoverned boundary is visible on the issue. Best-effort — never fails the
    # move (the canonical record is the journal where one is kept, the tracker
    # otherwise).
    if projection == "full" and not is_bypass_audit:
        _gh_comment(
            args.issue_number,
            _render_provenance_comment(invoker, current_state, args.to),
            config,
        )

    # Forward cascade. Each ancestor step it writes is journaled, where a journal is
    # kept, the way this move was, by the same actor, with this move named as the
    # reason. No hook follows a cascaded step and no audit comment; at `full` each
    # ancestor moved gets a provenance comment naming this move.
    if cascade is not None:
        _run_forward_cascade(cascade, cascade_context)

    print(f"\n[ok] transitioned #{args.issue_number}: {current_state} → {args.to}")

    # Fire after_move_issue hooks per DEC-024. The occurrence is the issue's
    # count of landed moves, the one the transition audit key counts by: the
    # journal's length as read before this move or, where no journal is kept,
    # the timeline's state-label events, read after it and only if a
    # `post-comment` hook is about to post. Either has grown by the time the
    # issue can make the same transition again, so its hook comment posts again
    # (#1243).
    fire_hooks(
        "after_move_issue",
        context={
            "issue": {
                "number": args.issue_number,
                "title": str(issue.get("title", "")) if issue else "",
            },
            "transition": {"from": current_state, "to": args.to},
        },
        config=config,
        capability_root=capability_root,
        occurrence=lambda: _landed_moves(args.issue_number, engine_status, config, substrate_map),
    )

    return 0


# ---- planning helpers ------------------------------------------------


@dataclass(frozen=True)
class Plan:
    issue_number: int
    add_label: str | None
    remove_label: str | None


def _compute_plan(
    *,
    issue_number: int,
    current_state: str,
    target_state: str,
    state_on_board: bool,
    labels: list[str],
    substrate_map: axis_labels.SubstrateMap | None = None,
) -> Plan:
    """The label add/remove pair for a state move, or an empty plan.

    ``state_on_board`` is the carriage answer from `_lib/axis_carriage`, not a
    read of ``has_projects_v2_board``: under a map binding `state` to the
    adopter's own labels, a configured board must NOT suppress the label write
    ([project-management:DEC-051-axis-carriage-activation]).
    """
    if state_on_board:
        return Plan(issue_number=issue_number, add_label=None, remove_label=None)
    # Label substrate. The state write is RESOLVED through the seam's write-path
    # resolver (ADR-026 sole-constructor + fail-closed): greenfield (no
    # substrate-map) resolves to the kit's own `state:<value>`; a present map
    # that binds state via a `derive` predicate (or marks it unsupported / omits
    # it) returns DEGRADE — and on a derive-bound state the open/closed substrate
    # CARRIES the state, so the kit writes (and removes) NO `state:*` label
    # (ADR-026 §5). The wrapper's domain side-effects still fire — only this
    # label write degrades.
    new_label_resolved = axis_labels.resolve_write("state", target_state, substrate_map)
    if not isinstance(new_label_resolved, str):
        # DEGRADE: state lives on the open/closed substrate, not a kit label.
        # Touch no `state:*` label (neither add the new nor strip a prior one).
        return Plan(issue_number=issue_number, add_label=None, remove_label=None)
    new_label = new_label_resolved
    old_label = None
    # Map-aware stale search. A prefix-only match (`is_axis_label`) finds the kit's
    # `state:*` and nothing else — but under a `label` binding the substrate IS the
    # adopter's own label name, which carries no prefix. `resolve_write` would then
    # add their new state label while the old one stayed on the issue: two states on
    # a single-valued axis, and no gate reads the adopter's vocabulary to notice.
    # The seam's `carried_labels` matches both the kit prefix and the binding's
    # declared values, so greenfield is unchanged and the bound case is repaired.
    for lbl in axis_labels.carried_labels("state", labels, substrate_map):
        if lbl != new_label:
            old_label = lbl
            break
    return Plan(issue_number=issue_number, add_label=new_label, remove_label=old_label)


def _print_plan(plan: Plan) -> None:
    print("\nplan:")
    if plan.add_label:
        print(f"  + add label {plan.add_label!r}")
    if plan.remove_label:
        print(f"  - remove label {plan.remove_label!r}")
    if not plan.add_label and not plan.remove_label:
        print("  · (substrate: board) — no label mutations.")


# ---- workflow-schema helpers ----------------------------------------


def _known_states(workflow: dict) -> set[str]:
    states = infer.workflow_process(workflow).get("states") or []
    out = set()
    for s in states:
        if isinstance(s, dict) and isinstance(s.get("id"), str):
            out.add(s["id"])
    return out


def _find_transition(
    workflow: dict,
    current_state: str,
    target_state: str,
    structural_type: str,
) -> Transition | None:
    """Look up the (from→to) transition in workflow.yaml.

    Falls back to None if the transition isn't listed *or* if the
    transition does not `applies_to` the given structural type.
    """
    transitions = infer.workflow_process(workflow).get("transitions") or []
    type_token = f"[issue-types:{structural_type}]"
    for t in transitions:
        if not isinstance(t, dict):
            continue
        if t.get("from") != current_state or t.get("to") != target_state:
            continue
        applies_to = t.get("applies_to") or []
        if type_token not in applies_to:
            continue
        severity_raw = str(t.get("severity", ""))
        return Transition(
            from_state=str(t.get("from")),
            to_state=str(t.get("to")),
            authorisation=str(t.get("authorisation", "")),
            severity=_severity_from_token(severity_raw),
            applies_to=tuple(applies_to),
        )
    return None


def _legal_targets(workflow: dict, current_state: str, structural_type: str) -> list[str]:
    """Enumerate legal target states for diagnostic output.

    Delegates to `lifecycle_inference.legal_targets`, shared with start-work's
    pre-mutation check (#942)."""
    return infer.legal_targets(workflow, current_state, structural_type)


def _is_forward(workflow: dict, current: str, target: str) -> bool:
    """Forward = increasing position in the canonical state ordering."""
    order = ["todo", "backlog", "in-progress", "review", "done"]
    try:
        return order.index(target) > order.index(current)
    except ValueError:
        return False


def _severity_from_token(token: str) -> str:
    """Parse `[validation-severity:<sev>]` tokens to a string severity."""
    m = re.match(r"\[validation-severity:([a-z-]+)\]", token or "")
    if not m:
        return SEVERITY_WARNING
    return m.group(1)


def _transition_audit_key(from_state: str, to_state: str, reason: str, landed_moves: str) -> str:
    """The idempotency key for one audited transition (#901).

    A retry must reproduce it exactly, and a genuinely new audited mutation must
    not. The components are what a retry repeats — the transition, the stripped
    reason — plus `landed_moves` (`_landed_moves`), which stays put across a
    failed attempt and has grown by the time the issue could make the same
    transition again. Without it, an issue moved back and re-promoted for the
    same reason would lose its second audit comment, breaking DEC-049's one
    comment per audited mutation from the other side. An empty `landed_moves`
    differs from every known one, so a retry across that boundary posts again —
    the safe direction for an audit trail.

    Hashed rather than interpolated (by `_lib.audit.audit_key`) so the reason
    cannot close the HTML comment early; the readable reason is in the comment's
    canonical line above it.
    """
    return _audit.audit_key(
        TRANSITION_AUDIT_WRITER,
        from_state or "",
        to_state,
        reason.strip(),
        landed_moves,
    )


def _bypass_journal_reason(bypass_reason: str) -> str | None:
    """The reason a bypassed move is journaled with: the justification its gate was
    overridden with, which its audit comment carries too — None for a move no gate
    was bypassed for, whose argv to the engine is then unchanged."""
    return f"bypass: {bypass_reason}" if bypass_reason else None


def _bypass_reason_missing(bypass: bool, bypass_reason: str | None) -> bool:
    """True when a `--bypass` override lacks the required non-empty reason.

    A `bypassable-with-audit` gate records the reason in the audit comment
    ([project-management:DEC-014-validation-severity-model]) and the
    override-flag convention ([project-management:DEC-046-override-flag-convention])
    requires it, so a bare `--bypass` with no reason must refuse rather than
    substitute a placeholder. Whitespace-only counts as missing. When
    `bypass` is False the flag is inert, so there is nothing to enforce.
    """
    return bool(bypass) and not (bypass_reason or "").strip()


def _infer_current_state(
    *,
    state: str,
    milestone: dict | None,
    labels: list[str],
    substrate_map: axis_labels.SubstrateMap | None = None,
) -> str:
    """Best-effort live state inference.

    Delegates to `lifecycle_inference.infer_current_state`, the single home of
    this precedence (closed→done; first state:* label; milestone→backlog; else
    todo). The same resolver backs the process detectors, so move-issue's local
    inference and the engine's detection agree by construction — behaviour
    parity (DEC-033). Kept as a thin local alias so the rest of this script (and
    the forward cascade's walk) reads naturally.

    Map-aware (ADR-026 §5): pass the adopter's `substrate_map` so this local
    fallback agrees with the engine's (now map-aware) detection under a present
    derive map — position resolves from open/closed, not a kit `state:*` label.
    `None` (the default) keeps the kit `state:*` precedence byte-unchanged, so
    callers that do not thread a map see today's behaviour exactly.
    """
    return infer.infer_current_state(
        state=state, milestone=milestone, labels=labels, substrate_map=substrate_map
    )


# ---- process-engine delegation (DEC-033 D4/D5) ----------------------
#
# move-issue delegates POSITION + JOURNAL to the shared process engine
# (`pkit process …`, COR-033), invoked by subprocess (never imported,
# ADR-020). It keeps the parity-critical wrapper-side concerns local:
# bypass/audit, TTY-confirm, placeholder/membership gates, cascade, and
# the domain side-effect (the label/board edit). The engine's detection
# (pm's classifier, `detect-state`) reproduces `_infer_current_state`
# exactly, so the engine position and the local inference agree; the
# engine is the single source of position truth (the seam-ordering
# contract in .pkit/process/README.md). The journal write is
# `_lib.move_journal`, the one path close-issue records its closes
# through too (#1231).


def _engine_status(issue_number: int) -> dict | None:
    """The issue's engine status payload (`pkit process status --json`), or None
    when the engine cannot be reached or answers with something unparseable.

    One read serves two consumers: `_position_from_status` (where the issue is)
    and `_landed_moves` (whether the project keeps a journal and, where it does,
    how many governed moves it holds — which keys the transition audit's retry
    detection).
    """
    try:
        proc = subprocess.run(
            [
                "pkit",
                "process",
                "status",
                PROCESS_ADDRESS,
                "--subject",
                str(issue_number),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _position_from_status(status: dict | None) -> str | None:
    """The resolved state id from an engine status payload.

    None when there is no payload or the position is missing/indeterminate —
    callers then fall back to the local inference (which uses the same
    precedence), so a missing `pkit` on PATH never blocks a move.
    """
    position = status.get("position") if isinstance(status, dict) else None
    if not isinstance(position, dict) or position.get("indeterminate"):
        return None
    state = position.get("state")
    return state if isinstance(state, str) else None


def _journal_length_from_status(status: dict | None) -> int | None:
    """How many entries the issue's engine journal holds, or None when unknown.

    The journal gains an entry only after a move's label write succeeds, so the
    count is unchanged across a failed attempt and its retry, and has grown by
    the time the issue could make the same transition again.
    """
    journal = status.get("journal") if isinstance(status, dict) else None
    return len(journal) if isinstance(journal, list) else None


def _journal_logging_off(status: dict | None) -> bool:
    """Whether the engine says this project keeps no journal (COR-033 point 7).

    Only an explicit `journal_logging.enabled: false` says so. A payload without
    the field comes from an engine that predates the setting and always kept a
    journal, and no payload at all says nothing either way.
    """
    logging = status.get("journal_logging") if isinstance(status, dict) else None
    return isinstance(logging, dict) and logging.get("enabled", True) is False


def _landed_moves(
    issue_number: int,
    status: dict | None,
    config: dict,
    substrate_map: axis_labels.SubstrateMap | None,
) -> str:
    """The transition audit key's "has a move landed since?" component.

    It must stay put across a failed attempt and its retry, and have grown by the
    time the issue could make the same transition again. What counts the moves
    follows where the project's audit trail is (DEC-049):

    * Where the project keeps a journal: the journal's length, as a bare number.
      A move is journaled only after its label write succeeds (#901).
    * Where it keeps none: the issue's count of state-label events on the GitHub
      timeline, labels put on and taken off (#954). A landed move changes the
      state label, and a failed label write changes nothing. The count is
      tagged, so it can never equal a journal length read on another attempt,
      after the project turned logging on or off.
    * Empty when it cannot be known: the engine is unreachable, the timeline
      cannot be read, or no label carries state (a board or a derivation does,
      and `move-issue` writes no label there). Two attempts that both land here
      look alike.

    The timeline is read only in the second case, and only on the bypass path
    that keys an audit comment and for a `post-comment` hook about to post on
    `after_move_issue`, which names its occurrence by the same count.
    """
    if not _journal_logging_off(status):
        length = _journal_length_from_status(status)
        return "" if length is None else str(length)
    if not state_timeline.label_carries_state(config, substrate_map):
        return ""
    events = state_timeline.state_label_events(
        issue_number,
        config,
        substrate_map,
        run=gh_run,
    )
    return "" if events is None else f"state-label-events:{len(events)}"


# Hand a completed move to the engine (`pkit process move --from`, best-effort):
# the one journaling path, shared with close-issue in `_lib.move_journal`.
# Bound under this module-private name, which the call sites below and the tests
# that stand in for it use.
_journal_move = move_journal.journal_move


def _journal_closed_issue_relabel(
    issue_number: int,
    target_state: str,
    *,
    workflow: dict,
    structural_type: str,
    milestone: dict | None,
    labels: list[str],
    substrate_map: axis_labels.SubstrateMap | None,
    actor: str | None,
    reason: str | None,
) -> None:
    """Record the move to done that relabelling a closed issue makes (#1231).

    A closed issue reads as done, so moving one to done finds it already there
    and only reconciles its label — the Review label a merge's `Closes #N` left
    on the issue `done-work` runs for, say. That label write is the close's
    move on the tracker, and the only one pkit makes: close-issue, which runs
    next, finds the label at done and records nothing. So it is recorded here,
    from where the old label placed the issue (`state_before_close`), as
    close-issue records a close: with ``reason`` — the merged PR's, which
    done-work passes, is the one close-issue gives the other issues the PR
    closed — and not at all when the workflow declares no such move for the
    issue's type (the engine does not read `applies_to`), which is warned about
    as a refused move is.
    """
    origin = infer.state_before_close(
        milestone=milestone, labels=labels, substrate_map=substrate_map
    )
    if origin is None or origin == target_state:
        return
    if _find_transition(workflow, origin, target_state, structural_type) is None:
        move_journal.report_unrecorded(
            issue_number,
            f"this move was not recorded: no transition {origin!r} → {target_state!r} "
            f"declared in workflow.yaml for {structural_type!r}",
        )
        return
    _journal_move(issue_number, origin, target_state, actor, reason=reason)


# ---- gh wrappers ----------------------------------------------------


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(
        issue_number,
        config,
        fields="title,body,labels,assignees,state,stateReason,milestone,url",
    )


# The close reason that says an issue finished its work. GitHub reports it for an
# issue closed as completed, which is how a merged pull request's `Closes #N`
# closes one; close-issue's won't-do closes as "not planned".
CLOSED_COMPLETED = "completed"


def _close_reason(issue: dict) -> str | None:
    """The reason a closed issue was closed with, as the tracker reports it —
    ``completed``, ``not planned``, ``duplicate`` — or None for an open issue,
    or one closed where the tracker reports no reason.

    ``gh issue view --json stateReason`` spells it as GitHub's GraphQL enum
    (``COMPLETED``, ``NOT_PLANNED``), and as an empty string where there is none.
    """
    if str(issue.get("state", "")).lower() != "closed":
        return None
    reason = str(issue.get("stateReason") or "").strip().lower().replace("_", " ")
    return reason or None


def _gh_apply_state_label(issue_number: int, plan: Plan, config: dict) -> bool:
    cmd = ["gh", "issue", "edit", str(issue_number)]
    if plan.add_label:
        cmd.extend(["--add-label", plan.add_label])
    if plan.remove_label:
        cmd.extend(["--remove-label", plan.remove_label])
    if len(cmd) == 4:  # nothing to change
        return True
    try:
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue edit failed (exit {proc.returncode}).\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _gh_comment(issue_number: int, body: str, config: dict) -> bool:
    try:
        proc = gh_run(
            ["gh", "issue", "comment", str(issue_number), "--body", body],
            config,
            check=False,
        )
    except FileNotFoundError:
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue comment failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _comment_failure(issue_number: int, body: str, config: dict) -> str | None:
    """Post ``body`` as a comment on the issue through the guarded `gh` path the
    label write takes: None when it was posted, else what went wrong, on one line."""
    try:
        proc = gh_run(
            ["gh", "issue", "comment", str(issue_number), "--body", body],
            config,
            check=False,
        )
    except FileNotFoundError:
        return "`gh` is not on PATH"
    if proc.returncode == 0:
        return None
    said = " ".join((proc.stderr or "").split())
    return f"gh issue comment exited {proc.returncode}" + (f": {said}" if said else "")


def _post_transition_audit_once(issue_number: int, body: str, key: str, config: dict) -> bool:
    """Post the transition audit comment unless that exact comment is already there.

    The shared `_lib.comment.post_audit_once` (#902): only a comment with exactly
    this body, posted unedited by the account `gh` posts as, counts — so neither a
    comment anyone else writes nor a same-account comment that merely contains
    `key` can suppress the record.

    True when the comment is posted or already present; False only when a post
    was needed and failed (the caller then aborts before mutating).
    """
    return post_audit_once(
        "issue",
        issue_number,
        key,
        body,
        config,
        run=gh_run,
        present_note="transition audit comment already present; idempotent skip",
    )


# ---- forward cascade (DEC-006) ----------------------------------------
#
# A container's state follows the work under it: when an issue moves forward,
# each ancestor — its parent, that parent's parent, and so on to the top — that
# is behind is brought up to the issue's state, capped at in-progress. The walk
# is planned before anything is written, from one read of each ancestor, and
# printed as the preview. The engine is asked where an ancestor is only when the
# plan moves it, to revalidate that plan against a sibling's move made since. An
# ancestor the engine answers it cannot place is not written, and the walk stops
# there; where the engine cannot be reached at all (`pkit` missing, or exiting
# non-zero), the plan read from the labels is written. That narrows the race
# with a concurrent sibling; it does not close it.


@dataclass(frozen=True)
class _CascadeContext:
    """What the forward cascade reads and writes with, fixed for one run.

    ``invoker`` is who runs the move, and the cascade's moves are theirs;
    ``projection`` is the audit projection (DEC-049), at `full` of which each
    ancestor moved gets a provenance comment. ``levels`` are the issue types it
    moves (`_cascade_levels`), empty when workflow.yaml declares none."""

    workflow: dict
    issue_types: dict
    classification: dict
    config: dict
    substrate_map: axis_labels.SubstrateMap | None
    invoker: object
    projection: str
    levels: tuple[str, ...]

    @property
    def actor(self) -> str | None:
        """The invoker's GitHub login, which each cascaded move is journaled by."""
        return getattr(self.invoker, "github_login", None)


@dataclass(frozen=True)
class _MovedIssue:
    """The issue whose move the forward cascade follows, as the cascade reads it.

    ``origin`` is where its move started: the state it held before, or, for an
    issue already at the target, where its old label places it — None when
    nothing records that. ``closed_as`` is the close reason the tracker reports
    for it (`_close_reason`)."""

    number: int
    body: str
    structural_type: str | None
    origin: str | None
    target: str
    closed: bool
    closed_as: str | None


@dataclass(frozen=True)
class _Ancestor:
    """One ancestor as the plan read it: where its labels and milestone place it,
    and the states it moves through to reach the target, in order — empty when
    it is at or past the target, None when the workflow declares no way there."""

    number: int
    structural_type: str | None
    labels: tuple[str, ...]
    state: str
    steps: tuple[str, ...] | None


@dataclass(frozen=True)
class _CascadePlan:
    """The forward cascade one move makes: the ancestors it reached, lowest
    first, why the walk ended below the top when it did, and — where it ended at
    two parents that disagree — how to settle them."""

    mover: _MovedIssue
    target: str
    ancestors: tuple[_Ancestor, ...]
    stop: str | None
    settle: str | None = None

    @property
    def reason(self) -> str:
        """The reason each cascaded step is journaled with (`_cascade_reason`)."""
        return _cascade_reason(self.mover)


@dataclass(frozen=True)
class _AncestorOutcome:
    """What the cascade did to one ancestor, as the closing block says it.

    ``complete`` is False when the ancestor was not fully moved and journaled;
    ``behind`` when it was left behind the target in a way running the move again
    can repair; ``stops_walk`` when nothing above it is moved. ``why`` holds the
    lines printed under it saying why the engine could not place it — the
    engine's causes, and what its predicates said (`_lib/engine_said`)."""

    number: int
    said: str
    complete: bool = True
    behind: bool = False
    stops_walk: bool = False
    why: tuple[str, ...] = ()


def _cascade_forward_target(child_target: str) -> str:
    """Return the container-safe forward-cascade target for a given child state.

    The forward cascade is scoped to todo → backlog → in-progress (DEC-006,
    amendment #38). Containers do not enter Review — Review models an open PR
    for a leaf Task; a container has no PR of its own. When a child reaches
    review or done, ancestors are brought to at most in-progress.
    """
    _FORWARD_CASCADE_CAP = "in-progress"
    order = ["todo", "backlog", "in-progress", "review", "done"]
    try:
        cap_idx = order.index(_FORWARD_CASCADE_CAP)
        child_idx = order.index(child_target)
    except ValueError:
        return child_target
    return order[min(child_idx, cap_idx)]


# Where an issue's move to done comes from when it finished work, not abandoned
# it: a move to done from todo or backlog is a won't-do close.
_COMPLETING_ORIGINS = ("in-progress", "review")


def _forward_cascade_target(mover: _MovedIssue) -> str | None:
    """The state the forward cascade brings ancestors up to after ``mover``'s
    move, or None when it brings up none.

    A move to done brings ancestors up only when it finished work
    (`_finished_work`)."""
    if mover.target == "done" and not _finished_work(mover):
        return None
    target = _cascade_forward_target(mover.target)
    return target if target in ("backlog", "in-progress") else None


def _finished_work(mover: _MovedIssue) -> bool:
    """Whether a move to done finished the issue's work rather than dropped it.

    It did from in-progress or review, and did not from todo or backlog — a
    won't-do close. Where the issue's label already reads done, so where it
    came from is not recorded, its close reason tells: completed finished it;
    any other reason, or none reported, does not say it did."""
    if mover.origin in _COMPLETING_ORIGINS:
        return True
    if mover.origin in ("todo", "backlog"):
        return False
    return mover.closed_as == CLOSED_COMPLETED


def _no_cascade_to_done(mover: _MovedIssue) -> str:
    """Why a move to done brings no ancestor up (`_finished_work`)."""
    if mover.origin in ("todo", "backlog"):
        return f"a move to done from {mover.origin} is a won't-do close"
    if mover.closed_as is not None:
        return f"#{mover.number} closed as {mover.closed_as}, not as completed"
    return (
        f"#{mover.number} already reads done and no close reason is reported for it, so "
        "whether it was completed or dropped as won't-do cannot be told; the next forward "
        "move under its ancestors brings them level"
    )


def _cascade_reason(mover: _MovedIssue) -> str:
    """The reason each forward-cascaded step is journaled with: the move of the
    issue that caused it (#1214), or, where the issue was already in place, the
    state it holds."""
    if mover.origin is None or mover.origin == mover.target:
        return f"forward cascade from #{mover.number}: at {mover.target}"
    return f"forward cascade from #{mover.number}: {mover.origin} → {mover.target}"


def _rerun_condition(mover: _MovedIssue) -> str | None:
    """What must hold, beyond its cause being fixed, for running ``mover``'s
    move again to finish a cascade cut short: "" for nothing more, None when
    running it again cannot finish it.

    Running a move again finishes the cascade from the no-op path, where a move
    to done brings ancestors up only for an issue closed as completed
    (`_finished_work`). An issue still open must close first; one closed for
    another reason, or with none reported, never brings them up that way."""
    if mover.target != "done" or mover.closed_as == CLOSED_COMPLETED:
        return ""
    if not mover.closed:
        return f"#{mover.number} has closed as completed"
    return None


def _finish_advice(mover: _MovedIssue, cause: str) -> str:
    """The line saying how to finish a cascade cut short, once ``cause`` holds."""
    condition = _rerun_condition(mover)
    if condition is None:
        return (
            "→ the next forward move under these ancestors brings them level; running "
            f"this move again would not, as #{mover.number} reads done without a close "
            "reported as completed."
        )
    when = " and ".join(part for part in (cause, condition) if part)
    return (
        f"→ run `move-issue {mover.number} --to {mover.target}` again once {when}: the "
        "cascade is idempotent, and brings level what is still behind."
    )


def _state_is_behind(current: str, target: str) -> bool:
    """Whether ``current`` comes before ``target`` in the lifecycle order.

    False for a state outside it — the collapsed ``open`` / ``blocked`` a
    `derive` binding reads — so such an ancestor is left alone, never moved."""
    order = ["todo", "backlog", "in-progress", "review", "done"]
    try:
        return order.index(current) < order.index(target)
    except ValueError:
        return False


def _cascade_levels(workflow: dict) -> tuple[str, ...]:
    """The issue types the forward cascade moves: `cascade.forward`'s
    `applies_to_levels` in workflow.yaml, as type names — empty when the list is
    missing or names none, which the cascade reports as the schema error it is
    rather than reading every parent as no container."""
    cascade = workflow.get("cascade") if isinstance(workflow, dict) else None
    forward = cascade.get("forward") if isinstance(cascade, dict) else None
    tokens = forward.get("applies_to_levels") if isinstance(forward, dict) else None
    levels = []
    for token in tokens or []:
        m = re.fullmatch(r"\[issue-types:([a-z0-9-]+)\]", str(token))
        if m:
            levels.append(m.group(1))
    return tuple(levels)


def _cascade_steps(
    workflow: dict, current: str, target: str, structural_type: str | None, levels: tuple[str, ...]
) -> tuple[str, ...] | None:
    """The states an ancestor at ``current`` moves through to reach ``target``,
    in order, each a transition workflow.yaml declares for its type: empty when
    it is at or past the target, None when no declared path leads there.

    The shortest declared path (`composed_move.moves_before`) and then the
    target, so an ancestor in todo goes to backlog first: no todo → in-progress
    is declared, and the engine records only declared moves. An ancestor whose
    type cannot be told takes the path every type the cascade moves declares.
    """
    if not _state_is_behind(current, target):
        return ()
    paths = {
        _declared_path(workflow, current, target, kind)
        for kind in ((structural_type,) if structural_type else levels)
    }
    if len(paths) != 1:
        return None
    return paths.pop()


def _declared_path(
    workflow: dict, current: str, target: str, structural_type: str
) -> tuple[str, ...] | None:
    """The states on the shortest declared path from ``current`` to ``target``
    for ``structural_type``, the target last; None when none leads there."""
    before = composed_move.moves_before(workflow, current, target, structural_type)
    if before or target in infer.legal_targets(workflow, current, structural_type):
        return (*before, target)
    return None


def _cascade_not_run(context: _CascadeContext, target: str) -> str | None:
    """Why the forward cascade does not run, or None when it does.

    It writes an ancestor's state as a label, so it runs only where the kit
    writes the state as one: the kit's own `state:*` labels, or an adopter's
    `label:` binding that has a value for every state the walk may write. Where
    a board carries the state, a derivation, the title, or nothing, no label is
    written and nothing would be recorded for an ancestor.
    """
    config, substrate_map = context.config, context.substrate_map
    if not state_timeline.label_carries_state(config, substrate_map):
        where = axis_carriage.describe("state", config, substrate_map)
        return f"state is carried {where}, and the forward cascade writes state only as a label"
    order = infer.STATE_ORDER
    for state in order[order.index("backlog") : order.index(target) + 1]:
        if not isinstance(axis_labels.resolve_write("state", state, substrate_map), str):
            return f"the state label binding has no value for {state!r}"
    return None


def _label_names(issue: dict) -> list[str]:
    return [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]


def _parents_disagree(
    number: int, named: int | None, native: containment.NativeParent | None
) -> str | None:
    """What to say when issue ``number``'s native parent is not the parent its
    first line names (``named``), or None when they agree or it has no native
    parent — a tracker that reports none leaves the first line the only record.
    """
    if native is None or (named is not None and native.is_issue(named)):
        return None
    if named is None:
        return (
            f"#{number}'s first line names no parent issue, its native parent is {native.ref}; "
            f"nothing is written to {native.ref}"
        )
    return (
        f"#{number}'s first line names #{named}, its native parent is {native.ref}; "
        "nothing is written to either parent"
    )


def _settle_parents(number: int, named: int | None, native: containment.NativeParent) -> str:
    """How to settle the disagreement `_parents_disagree` reports: the native
    parent wins and the first line is rewritten to name it
    ([project-management:DEC-005-linking-and-containment]) — which no first-line
    form can do for a native parent in another repository."""
    if native.repository is None:
        return (
            f"→ the native parent wins (DEC-005): `set-field {number} --parent {native.number}` "
            f"rewrites #{number}'s first line to name it."
        )
    move_link = (
        f"; if #{named} is its parent, `set-field {number} --parent {named}` moves the native "
        "link under it"
        if named is not None
        else ""
    )
    return (
        f"→ {native.ref} is in another repository, which no first-line form can name and the "
        f"forward cascade does not walk into{move_link}."
    )


def _plan_forward_cascade(
    mover: _MovedIssue, parent: int, target: str, context: _CascadeContext
) -> _CascadePlan:
    """Walk from the moved issue's ``parent`` to the top of its hierarchy,
    reading each ancestor once.

    Each step up follows the parent the ancestor's first line names
    (`body_parent_ref.parent_issue`). The read of an ancestor also carries its
    native parent, so where that differs from the parent its first line names
    the walk stops there: the ancestor is moved, and nothing above it — the
    native parent wins, and the first line is to be rewritten to name it
    (DEC-005). The walk also stops at an ancestor it cannot read, at one that is
    recognisably not a container (one whose type cannot be told is moved, as an
    untyped tree always was), at one it has already passed, and at one whose
    first line looks like a parent-ref its type does not allow. An ancestor at
    or past the target is left alone and the walk goes on above it, so a chain
    an earlier move left behind is brought level.
    """
    ancestors: list[_Ancestor] = []
    visited = {mover.number}
    child, number = mover.number, parent
    stop = settle = None
    while number is not None:
        if number in visited:
            stop = f"#{child} names #{number} as its parent, which the walk has passed already"
            break
        visited.add(number)
        record = containment.read_issue_record(context.config, issue_number=number)
        if isinstance(record, containment.UnreadIssue):
            stop = f"#{number}, named as #{child}'s parent, could not be read: {record.detail}"
            break
        issue = record.issue
        labels = _label_names(issue)
        kind = infer_structural_type(
            str(issue.get("title", "")),
            context.issue_types,
            classification=context.classification,
            labels=labels,
        )
        if kind is not None and kind not in context.levels:
            stop = f"#{number}, named as #{child}'s parent, is a {kind}, not a container"
            break
        state = _infer_current_state(
            state=str(issue.get("state", "")).lower(),
            milestone=issue.get("milestone") or {},
            labels=labels,
            substrate_map=context.substrate_map,
        )
        steps = _cascade_steps(context.workflow, state, target, kind, context.levels)
        ancestors.append(_Ancestor(number, kind, tuple(labels), state, steps))
        body = str(issue.get("body") or "")
        unrecognised = body_parent_ref.unrecognised_parent_line(body, kind, context.issue_types)
        if unrecognised is not None:
            stop = f"#{number}'s {unrecognised}"
            break
        named = body_parent_ref.parent_issue(body, kind, context.issue_types)
        disagreement = _parents_disagree(number, named, record.parent)
        if disagreement is not None and record.parent is not None:
            stop, settle = disagreement, _settle_parents(number, named, record.parent)
            break
        child, number = number, named
    return _CascadePlan(
        mover=mover, target=target, ancestors=tuple(ancestors), stop=stop, settle=settle
    )


def _describe_ancestor(ancestor: _Ancestor) -> str:
    kind = f" ({ancestor.structural_type})" if ancestor.structural_type else ""
    return f"#{ancestor.number}{kind}"


def _preview_forward_cascade(mover: _MovedIssue, context: _CascadeContext) -> _CascadePlan | None:
    """Plan the forward cascade a move makes and print it: each ancestor with
    the steps it will take, or why it is left alone, and where the walk stops.

    None when there is nothing to run: the move brings no ancestor up, the kit
    does not write the state as a label, the workflow names no level the
    cascade moves, or the walk has nowhere to start (`_first_parent`) — each
    said in a line, except an issue with no parent at all.
    """
    named = body_parent_ref.parent_issue(mover.body, mover.structural_type, context.issue_types)
    target = _forward_cascade_target(mover)
    if target is None:
        if mover.target == "done" and named is not None:
            why = _no_cascade_to_done(mover)
            print(f"\n[cascade] the forward cascade moves no ancestor: {why}.")
        return None
    not_run = _cascade_not_run(context, target)
    if not_run is not None:
        if named is not None:
            print(f"\n[cascade] the forward cascade does not run: {not_run}.")
        return None
    if not context.levels:
        print(
            "\n[warn] the forward cascade does not run: workflow.yaml declares no "
            "`cascade.forward.applies_to_levels`, so which issue types it moves is not known.",
            file=sys.stderr,
        )
        return None
    parent = _first_parent(mover, named, context)
    if parent is None:
        return None
    plan = _plan_forward_cascade(mover, parent, target, context)
    print(f"\n[cascade] forward cascade — each ancestor brought up to {target}:")
    for ancestor in plan.ancestors:
        if ancestor.steps is None:
            what = f"{ancestor.state}; workflow.yaml declares no way to {target}"
        elif ancestor.steps:
            what = " → ".join((ancestor.state, *ancestor.steps))
        else:
            what = f"{ancestor.state}; left alone"
        print(f"  {_describe_ancestor(ancestor)}: {what}")
    if plan.stop is not None:
        print(f"  [warn] {plan.stop}; the walk stops there.", file=sys.stderr)
    if plan.settle is not None:
        print(f"  {plan.settle}", file=sys.stderr)
    return plan


def _first_parent(mover: _MovedIssue, named: int | None, context: _CascadeContext) -> int | None:
    """The parent the walk starts from — ``named``, the one the moved issue's
    first line names — or None when it starts nowhere.

    The moved issue's native parent is held to its first line as each
    ancestor's is: read once, here, where a cascade is otherwise set to run.
    Where they disagree the walk starts nowhere, and nothing is written to
    either parent's chain. It starts nowhere, too, from a first line that looks
    like a parent-ref the issue's type does not allow, and from one whose native
    parent cannot be read to compare. Each is said in a warning, the last two
    with how to finish; an issue whose first line names no parent and which has
    no native one has nothing to say.
    """
    number = mover.number
    unrecognised = body_parent_ref.unrecognised_parent_line(
        mover.body, mover.structural_type, context.issue_types
    )
    if unrecognised is not None:
        print(
            f"\n[warn] #{number}'s {unrecognised}; the forward cascade walks nothing from it.",
            file=sys.stderr,
        )
        return None
    record = containment.read_issue_record(context.config, issue_number=number)
    if isinstance(record, containment.UnreadIssue):
        if named is None:
            return None
        print(
            f"\n[warn] the forward cascade walks nothing: #{number}'s record could not be read "
            f"to hold its native parent to #{named}, the parent its first line names "
            f"({record.detail}).",
            file=sys.stderr,
        )
        print(f"  {_finish_advice(mover, '`gh` answers')}", file=sys.stderr)
        return None
    disagreement = _parents_disagree(number, named, record.parent)
    if disagreement is not None and record.parent is not None:
        print(f"\n[warn] the forward cascade walks nothing: {disagreement}.", file=sys.stderr)
        print(f"  {_settle_parents(number, named, record.parent)}", file=sys.stderr)
        print(f"  {_finish_advice(mover, 'the two agree')}", file=sys.stderr)
        return None
    return named


def _engine_position(issue_number: int) -> tuple[bool, str | None, tuple[str, ...]]:
    """(reached, state, why): whether the engine answered, the position it gave —
    None from an engine that answered is a position it cannot tell — and, for
    such a position, the lines saying why, as the engine's status gives it."""
    status = _engine_status(issue_number)
    if status is None:
        return False, None, ()
    state = _position_from_status(status)
    if state is not None:
        return True, state, ()
    return True, None, tuple(engine_said.unplaced_lines(status, "    "))


def _run_forward_cascade(plan: _CascadePlan, context: _CascadeContext) -> None:
    """Make the planned cascade, ancestor by ancestor, lowest first, and end with
    one block saying what became of each.

    An ancestor the cascade fails to move does not stop it: one above it may be
    ahead of it. The block is a warning when anything is left undone; the issue's
    own move stands either way, and running it again repairs what a re-run can.
    """
    outcomes: list[_AncestorOutcome] = []
    unreached: list[int] = []
    for ancestor in plan.ancestors:
        if outcomes and outcomes[-1].stops_walk:
            unreached.append(ancestor.number)
            continue
        outcomes.append(_cascade_ancestor(ancestor, plan, context))
    _print_cascade_report(plan, outcomes, unreached)


def _cascade_ancestor(
    ancestor: _Ancestor, plan: _CascadePlan, context: _CascadeContext
) -> _AncestorOutcome:
    """Bring one ancestor up to the target, as planned unless the engine says
    the plan is stale."""
    number = ancestor.number
    if ancestor.steps is None:
        return _AncestorOutcome(
            number,
            f"not moved: workflow.yaml declares no way from {ancestor.state} to {plan.target}",
            complete=False,
        )
    if not ancestor.steps:
        return _AncestorOutcome(number, f"left alone at {ancestor.state}")
    origin, steps, labels = ancestor.state, ancestor.steps, list(ancestor.labels)
    reached, engine_state, why = _engine_position(number)
    if reached and engine_state is None:
        return _AncestorOutcome(
            number,
            "not moved: the engine cannot tell where it is, so the walk stops here",
            complete=False,
            behind=True,
            stops_walk=True,
            why=why,
        )
    if engine_state is not None and engine_state != origin:
        steps = _cascade_steps(
            context.workflow, engine_state, plan.target, ancestor.structural_type, context.levels
        )
        if steps is None:
            return _AncestorOutcome(
                number,
                f"not moved: workflow.yaml declares no way from {engine_state} to {plan.target}",
                complete=False,
            )
        if not steps:
            return _AncestorOutcome(number, f"left alone at {engine_state} (the engine's reading)")
        # Moved since the plan read it: write from its labels as they are now.
        record = containment.read_issue_record(context.config, issue_number=number)
        if isinstance(record, containment.UnreadIssue):
            return _AncestorOutcome(
                number,
                f"not moved: the engine places it at {engine_state} and it could not be read "
                f"again ({record.detail})",
                complete=False,
                behind=True,
            )
        origin, labels = engine_state, _label_names(record.issue)
    return _step_ancestor(number, origin, steps, labels, plan.reason, context)


def _step_ancestor(
    number: int,
    origin: str,
    steps: tuple[str, ...],
    labels: list[str],
    reason: str,
    context: _CascadeContext,
) -> _AncestorOutcome:
    """Write each step as its own label edit, computed from the labels as the
    step before left them, and journal it; then project the steps that landed
    (`_project_cascaded_move`).

    A step whose label landed is followed by the next whether or not the engine
    took it, so the ancestor never rests between the two writes of one step; a
    write that fails ends the ancestor there, at the state the step before left
    it in, carrying that state's label alone."""
    reached = [origin]
    said: list[str] = []
    all_journaled = True
    current = origin
    for step in steps:
        edit = _compute_plan(
            issue_number=number,
            current_state=current,
            target_state=step,
            state_on_board=False,
            labels=labels,
            substrate_map=context.substrate_map,
        )
        print(f"[cascade] #{number}: {current} → {step}")
        if not _gh_apply_state_label(number, edit, context.config):
            said.append(f"{current} → {step} not written (the label write failed)")
            _project_cascaded_move(number, reached, reason, context)
            return _AncestorOutcome(
                number,
                "; ".join(said) if len(said) > 1 else f"not moved: {said[0]}",
                complete=False,
                behind=True,
            )
        labels = [lbl for lbl in labels if lbl != edit.remove_label]
        if edit.add_label and edit.add_label not in labels:
            labels.append(edit.add_label)
        journaled = _journal_move(number, current, step, context.actor, reason=reason)
        said.append(f"{current} → {step}" if journaled else f"{current} → {step} (not journaled)")
        all_journaled = all_journaled and bool(journaled)
        reached.append(step)
        current = step
    _project_cascaded_move(number, reached, reason, context)
    if not all_journaled:
        return _AncestorOutcome(number, "; ".join(said), complete=False)
    return _AncestorOutcome(number, " → ".join(reached))


def _project_cascaded_move(
    number: int, reached: list[str], reason: str, context: _CascadeContext
) -> None:
    """At the `full` audit projection, post on ancestor ``number`` the provenance
    comment a governed move gets (DEC-049), naming the move that caused it.

    One comment for the steps that landed in this run, so an ancestor taken
    through Backlog to In Progress gets one comment naming both; none when no
    step landed, and none at any other projection. A step is written once — a
    re-run finds the ancestor level and moves it no further — so a step is never
    in two comments. Posted whether or not the engine journaled the steps, as the
    moved issue's own comment is. A comment that fails to post is one warning
    line, and the move stands."""
    if context.projection != _audit.PROJECTION_FULL or len(reached) < 2:
        return
    body = _render_provenance_comment(context.invoker, *reached, cause=reason)
    failure = _comment_failure(number, body, context.config)
    if failure is not None:
        print(
            f"  [warn] #{number}: its provenance comment was not posted ({failure}); "
            "the move stands.",
            file=sys.stderr,
        )


def _print_cascade_report(
    plan: _CascadePlan, outcomes: list[_AncestorOutcome], unreached: list[int]
) -> None:
    """The cascade's closing block: every ancestor's outcome, a warning when
    anything was left undone, and how to repair what can be repaired — two
    parents that disagree settled, and the rest by running the move again where
    that finishes it (`_finish_advice`)."""
    complete = plan.stop is None and not unreached and all(o.complete for o in outcomes)
    stream = sys.stdout if complete else sys.stderr
    head = "[cascade]" if complete else "[warn]"
    status = "" if complete else ", not completed"
    print(f"\n{head} forward cascade from #{plan.mover.number}{status}:", file=stream)
    for outcome in outcomes:
        print(f"  #{outcome.number}: {outcome.said}", file=stream)
        for line in outcome.why:
            print(line, file=stream)
    for number in unreached:
        print(f"  #{number}: not reached", file=stream)
    if plan.stop is not None:
        print(f"  the walk stopped: {plan.stop}", file=stream)
    if plan.settle is not None:
        print(f"  {plan.settle}", file=stream)
    if unreached or plan.settle is not None or any(o.behind for o in outcomes):
        print(f"  {_finish_advice(plan.mover, 'the cause is fixed')}", file=stream)


# ---- I/O helpers ----------------------------------------------------


def _read_yaml(path: Path, yaml_loader: YAML) -> dict:
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    data = _read_yaml(capability_root / "project" / "members.yaml", yaml_loader)
    members = data.get("members") or []
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
