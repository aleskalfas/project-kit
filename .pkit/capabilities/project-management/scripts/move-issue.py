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
README.md). The engine's detectors reproduce this script's inference
precedence, so position is identical (behaviour parity is the acceptance
bar). The parity-critical wrapper-side concerns STAY here: membership,
placeholder, authorisation/bypass/TTY, and the forward cascade.

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

Cascade per DEC-006 fires upward on forward transitions; the script
walks the parent chain via the issue body's parent-ref line.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/move-issue.py 42 --to in-progress

Or via the dispatcher (per COR-021):
  pkit project-management move-issue 42 --to in-progress

Exit codes:
  0  transitioned (or dry-run reported)
  1  membership refusal / authorisation refusal
  2  usage error (unknown state, illegal transition, issue not found)
  3  gh failure
"""

from __future__ import annotations

import argparse
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
from _lib import audit as _audit  # noqa: E402
from _lib import axis_carriage  # noqa: E402
from _lib import axis_labels  # noqa: E402
from _lib import bootstrap_gate  # noqa: E402
from _lib import classification_rules  # noqa: E402
from _lib import lifecycle_inference as infer  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.hooks import fire_hooks  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.placeholder_detection import (  # noqa: E402
    PHASE_TRANSITION,
    detect_placeholder_residuals,
)


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


def _pkit_version() -> str:
    """Best-effort pkit version for a `full`-projection provenance stamp."""
    try:
        proc = subprocess.run(
            ["pkit", "--version"], capture_output=True, text=True, check=False,
        )
    except OSError:
        return ""
    if proc.returncode != 0:
        return ""
    parts = proc.stdout.strip().replace(",", " ").split()
    return parts[-1] if parts else ""


def _render_provenance_comment(invoker, from_state, to_state) -> str:
    """DEC-049 `full` projection: a provenance-stamped record of a governed move,
    carrying the pkit version — the governed-vs-ungoverned boundary made visible on
    the issue. Absence of such a comment beside a timeline label change flags an
    out-of-band mutation."""
    actor = (getattr(invoker, "github_login", None)
             or getattr(invoker, "email", None) or "unknown")
    version = _pkit_version()
    stamp = f" — pkit {version}" if version else ""
    move = f"{from_state} → {to_state}" if from_state else str(to_state)
    return f"{_AUDIT_MARKER}\n{actor} moved {move} (governed by pkit){stamp}"


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
        help=(
            "Target state: one of todo, backlog, in-progress, review, done."
        ),
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
            "Reason recorded in the audit comment; required (non-empty) "
            "whenever --bypass is set — a bare --bypass is refused."
        ),
    )
    parser.add_argument(
        "--no-cascade",
        action="store_true",
        help="Skip the forward-cascade walk on parent issues.",
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
    issue_types = _read_yaml(
        capability_root / "schemas" / "issue-types.yaml", yaml_loader
    )
    classification = _read_yaml(
        capability_root / "schemas" / "classification.yaml", yaml_loader
    )
    body_format = _read_yaml(
        capability_root / "schemas" / "body-format.yaml", yaml_loader
    )
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

    structural_type = _infer_structural_type(
        title, issue_types, classification, labels
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

    # Position: read from the engine (DEC-033 D7 — read, don't re-infer). The
    # engine's detectors reproduce this script's inference precedence (and are
    # now map-aware, ADR-026 §5), so the result is identical; fall back to the
    # local inference only when the engine is unreachable (e.g. `pkit` not on
    # PATH), so a move is never blocked. The fallback is threaded the same map so
    # it agrees with the engine under a present derive binding.
    current_state = _engine_position(args.issue_number)
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
        return 0

    # Look up the transition.
    transition = _find_transition(
        workflow, current_state, args.to, structural_type
    )
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

    # Cascade preview.
    cascade_targets: list[int] = []
    if not args.no_cascade and _is_forward(workflow, current_state, args.to):
        cascade_targets = _walk_parent_chain(body)
        if cascade_targets:
            print(
                f"\n[cascade] forward cascade will visit parents: "
                f"{', '.join(f'#{n}' for n in cascade_targets)}"
            )

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # Audit-comment projection (DEC-049): the engine journal records this move
    # regardless; `audit.projection` controls the GitHub comment projection —
    # `off` posts nothing, `audit` (default) posts only override justifications,
    # `full` posts a provenance-stamped comment for every governed move.
    projection = _audit_projection(config)
    is_bypass_audit = (
        transition.authorisation == "user"
        and transition.severity == SEVERITY_BYPASSABLE
        and args.bypass
    )
    if projection != "off" and is_bypass_audit:
        # Reason is guaranteed non-empty here: the bypassable authorisation
        # gate above refuses a --bypass without a non-empty --bypass-reason.
        # move-issue is the sole writer of the TRANSITION audit comment (DEC-049): it renders the
        # one canonical comment from the schema template; wrappers pass the reason
        # through rather than posting their own (killing the #672 double-post).
        reason = (args.bypass_reason or "").strip()
        audit_comment = _render_audit_comment(capability_root, invoker, reason)
        if not _gh_comment(args.issue_number, audit_comment, config):
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
    # label/board edit) is applied above; now journal the move via the engine.
    # Best-effort — a refusal or missing `pkit` never fails the move, since
    # live detection stays authoritative.
    #
    # `--actor` is the resolved GitHub login of the invoker (not the
    # authorisation token), so the engine's cross-authority gate compares
    # like-with-like against an artifact's `produced_by` login (COR-033 P4).
    _journal_move(args.issue_number, args.to, invoker.github_login)

    # DEC-049 `full` projection: post a provenance-stamped comment for a governed
    # move not already covered by the bypass audit above, so the governed-vs-
    # ungoverned boundary is visible on the issue. Best-effort — never fails the
    # move (the engine journal is the canonical record).
    if projection == "full" and not is_bypass_audit:
        _gh_comment(
            args.issue_number,
            _render_provenance_comment(invoker, current_state, args.to),
            config,
        )

    # Forward cascade.
    if cascade_targets and not args.no_cascade:
        for parent_num in cascade_targets:
            ok = _cascade_parent(parent_num, args.to, config, substrate_map)
            if not ok:
                print(
                    f"[warn] cascade on #{parent_num} did not complete cleanly.",
                    file=sys.stderr,
                )

    print(
        f"\n[ok] transitioned #{args.issue_number}: "
        f"{current_state} → {args.to}"
    )

    # Fire after_move_issue hooks per DEC-024.
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
    substrate_map: "axis_labels.SubstrateMap | None" = None,
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
    return Plan(
        issue_number=issue_number, add_label=new_label, remove_label=old_label
    )


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


def _legal_targets(
    workflow: dict, current_state: str, structural_type: str
) -> list[str]:
    """Enumerate legal target states for diagnostic output."""
    transitions = infer.workflow_process(workflow).get("transitions") or []
    type_token = f"[issue-types:{structural_type}]"
    out: list[str] = []
    for t in transitions:
        if not isinstance(t, dict):
            continue
        if t.get("from") != current_state:
            continue
        if type_token not in (t.get("applies_to") or []):
            continue
        target = t.get("to")
        if isinstance(target, str):
            out.append(target)
    return out


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


def _infer_structural_type(
    title: str,
    issue_types: dict,
    classification: dict | None = None,
    labels: list[str] | None = None,
) -> str | None:
    """Infer the structural type, title prefix first, then the `type:*` label.

    PRECEDENCE: the title prefix wins; the `type:*` kind label is the fallback,
    consulted only when no prefix matches. (Structural-type inference also runs
    in create-issue / validate-issue / the engine; a future parity pass per
    DEC-033 should align those sites with this precedence rule.)

    Sources, in order:
    1. issue-types.yaml `types[*].title_prefix` — the structural-type
       prefixes ([EPIC], [Feature], [Umbrella], [Task]).
    2. classification.yaml `axes.type.title_prefix_by_value` — the
       kind-driven prefixes ([Bug], [Docs], [Test], [Refactor], [Chore]).
       Kind-prefixes are restricted to the `task` structural type.
    3. FALLBACK — the issue's `type:*` kind label, when no prefix matched.
       Only ever recovers `task` (see `_structural_type_from_kind_label`); a
       container with an edited-away prefix has no `type:*` label and stays
       unrecoverable, surfaced as malformed by the caller.
    """
    types = issue_types.get("types") or {}
    for type_name, entry in types.items():
        if not isinstance(entry, dict):
            continue
        prefix = entry.get("title_prefix", "")
        case = entry.get("title_case", "title")
        rendered = str(prefix)
        if case == "upper":
            rendered = rendered.upper()
        if title.startswith(f"[{rendered}] "):
            return str(type_name)

    # Check kind-driven prefixes from classification.yaml.
    # These only appear on Task-shape issues per the structural_restriction rule.
    if classification:
        prefix_by_value = (
            classification.get("axes", {})
            .get("type", {})
            .get("title_prefix_by_value", {})
        )
        for _kind_value, kind_prefix in prefix_by_value.items():
            if isinstance(kind_prefix, str) and title.startswith(f"[{kind_prefix}] "):
                return "task"

    # Fallback: recover the structural type from the `type:*` kind label when the
    # title prefix was edited away. Task-only by construction (see helper).
    if labels and classification:
        return _structural_type_from_kind_label(labels, classification)

    return None


def _structural_type_from_kind_label(
    labels: list[str],
    classification: dict,
) -> str | None:
    """Recover the structural type from the issue's `type:*` kind label.

    A `type:*` label carries only *kind* (bug/docs/test/refactor/maintenance/
    feature) and exists only on Tasks: per classification.yaml's
    `structural_restriction`, every non-feature kind maps to the single
    structural type `task`, while feature-kind containers (epic/feature/
    umbrella) carry no distinguishing `type:*` label. The kind→structural
    mapping is READ from `allowed_structural_types_per_kind` rather than
    hardcoded — a kind recovers a structural type only when its allowed-set is
    unambiguous (exactly one type), which is true for every task-only kind and
    false for the multi-valued `feature` kind. So this only ever recovers
    `task`; an ambiguous or unknown kind returns None.
    """
    kind = axis_labels.read("type", labels)
    if kind is None:
        return None
    # The kind→structural table is read through the shared _lib reader — the one
    # place `allowed_structural_types_per_kind` is parsed (COR-007 single source).
    allowed = classification_rules.allowed_structural_types_per_kind(classification)
    candidates = allowed.get(kind) if isinstance(allowed, dict) else None
    if isinstance(candidates, list) and len(candidates) == 1:
        only = candidates[0]
        return str(only) if isinstance(only, str) else None
    return None


def _infer_current_state(
    *,
    state: str,
    milestone: dict | None,
    labels: list[str],
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> str:
    """Best-effort live state inference.

    Delegates to `lifecycle_inference.infer_current_state`, the single home of
    this precedence (closed→done; first state:* label; milestone→backlog; else
    todo). The same resolver backs the process detectors, so move-issue's local
    inference and the engine's detection agree by construction — behaviour
    parity (DEC-033). Kept as a thin local alias so the rest of this script (and
    `_cascade_parent`) reads naturally.

    Map-aware (ADR-026 §5): pass the adopter's `substrate_map` so this local
    fallback agrees with the engine's (now map-aware) detection under a present
    derive map — position resolves from open/closed, not a kit `state:*` label.
    `None` (the default) keeps the kit `state:*` precedence byte-unchanged, so
    callers that do not thread a map see today's behaviour exactly.
    """
    return infer.infer_current_state(
        state=state, milestone=milestone, labels=labels, substrate_map=substrate_map
    )


def _walk_parent_chain(body: str) -> list[int]:
    """Extract parent issue numbers from the body's first non-blank lines.

    Recognises forms like `EPIC: #42`, `Feature: #99`, `Umbrella: #5`. A leading
    DEC-013 `Integration:` marker is skipped first (#763).
    """
    if not body:
        return []
    body = infer.strip_integration_marker(body)
    out: list[int] = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            if out:
                break
            continue
        m = re.match(r"^([A-Za-z]+):\s+#(\d+)", s)
        if not m:
            break
        out.append(int(m.group(2)))
        break  # parent-ref is one line by convention
    return out


# ---- process-engine delegation (DEC-033 D5/D7) ----------------------
#
# move-issue delegates POSITION + JOURNAL to the shared process engine
# (`pkit process …`, COR-033), invoked by subprocess (never imported,
# ADR-020). It keeps the parity-critical wrapper-side concerns local:
# bypass/audit, TTY-confirm, placeholder/membership gates, cascade, and
# the domain side-effect (the label/board edit). The engine's detectors
# reproduce `_infer_current_state` exactly, so the engine position and
# the local inference agree; the engine is the single source of position
# truth (the seam-ordering contract in .pkit/process/README.md).

PROCESS_ADDRESS = "project-management:issue-lifecycle"


def _engine_position(issue_number: int) -> str | None:
    """Read the issue's position from the engine (`pkit process status --json`).

    Returns the resolved state id, or None when the engine cannot be reached or
    returns no/indeterminate position — callers then fall back to the local
    inference (which uses the same precedence), so a missing `pkit` on PATH
    never blocks a move.
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
    position = payload.get("position") if isinstance(payload, dict) else None
    if not isinstance(position, dict) or position.get("indeterminate"):
        return None
    state = position.get("state")
    return state if isinstance(state, str) else None


def _journal_move(
    issue_number: int, target_state: str, actor: str | None
) -> None:
    """Journal the completed move via `pkit process move` (best-effort).

    Per the seam-ordering contract: the domain side-effect (the label/board
    edit) has ALREADY been applied by the caller; this only records the move in
    the engine's append-only journal. A refusal or a missing `pkit` is logged as
    a note and never fails the move — live detection stays authoritative, so the
    next `status` reflects the real position regardless.

    `actor` is the invoker's resolved GitHub login. The engine compares it
    against an authorisation artifact's `produced_by` login for the
    cross-authority gate (COR-033 P4). When it is None (login unresolved), we
    omit `--actor` and let the engine apply its own resolved-identity default.
    """
    argv = [
        "pkit",
        "process",
        "move",
        PROCESS_ADDRESS,
        "--to",
        target_state,
        "--subject",
        str(issue_number),
    ]
    if actor:
        argv += ["--actor", actor]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        print(
            "  [warn] `pkit` not on PATH — this move was NOT recorded in the engine "
            "journal (the canonical audit trail, DEC-049). The label/position is "
            "unaffected (live detection stays authoritative); re-run under `pkit` "
            "to journal it.",
            file=sys.stderr,
        )
        return
    if proc.returncode != 0:
        detail = (proc.stdout or proc.stderr or "").strip()
        print(
            "  [warn] this move was NOT recorded in the engine journal (the "
            f"canonical audit trail, DEC-049): {detail}. The label/position is "
            "unaffected; `pkit pm history <N> --check-drift` will show the gap.",
            file=sys.stderr,
        )


# ---- gh wrappers ----------------------------------------------------


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(
        issue_number, config,
        fields="title,body,labels,assignees,state,milestone,url",
    )


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
            f"error: gh issue edit failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
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


def _cascade_forward_target(child_target: str) -> str:
    """Return the container-safe forward-cascade target for a given child state.

    The forward cascade is scoped to todo → backlog → in-progress (DEC-006,
    amendment #38). Containers do not enter Review — Review models an open PR
    for a leaf Task; a container has no PR of its own. When a child reaches
    review or done, ancestors are bumped to at most in-progress.
    """
    _FORWARD_CASCADE_CAP = "in-progress"
    order = ["todo", "backlog", "in-progress", "review", "done"]
    try:
        cap_idx = order.index(_FORWARD_CASCADE_CAP)
        child_idx = order.index(child_target)
    except ValueError:
        return child_target
    return order[min(child_idx, cap_idx)]


def _cascade_parent(
    parent_num: int,
    target_state: str,
    config: dict,
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> bool:
    """Forward cascade — bump parent if it's behind.

    Conservative implementation: read parent state; if parent is behind
    the capped cascade target, label-edit it forward. Bypasses authorisation
    gates per DEC-006 ("forward cascade is automatic").

    The cascade target is capped at in-progress for containers: Review is a
    leaf/Task state and a container must never auto-enter it (DEC-006,
    amendment #38). A child moving to review or done bumps its ancestors to
    at most in-progress.
    """
    parent = _gh_get_issue(parent_num, config)
    if parent is None:
        return False
    parent_labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (parent.get("labels") or [])
    ]
    parent_state = _infer_current_state(
        state=str(parent.get("state", "")).lower(),
        milestone=parent.get("milestone") or {},
        labels=parent_labels,
        substrate_map=substrate_map,
    )
    # Cap the cascade target: containers top out at in-progress.
    cascade_target = _cascade_forward_target(target_state)
    # Under a derive binding the forward cascade is an INTENTIONAL no-op: parent_state
    # is the collapsed `open`/`blocked` (not in STATE_ORDER), so `_state_is_behind`
    # returns False and we exit here — and even if reached, `_compute_plan` would
    # DEGRADE the `state:*` write (no kit label written under a derive map). This is
    # correct (the open-ish collapse means there is no meaningful forward bump, and
    # you cannot write a kit `state:*` label under derive); do NOT "fix" the
    # ValueError-tolerant `_state_is_behind` into a crash on these derived ids.
    if not _state_is_behind(parent_state, cascade_target):
        return True  # already at or beyond the capped target.
    plan = _compute_plan(
        issue_number=parent_num,
        current_state=parent_state,
        target_state=cascade_target,
        # Same carriage question as the child's own move, asked the same way. It
        # was hardcoded False ("cascade only fires for label substrate"), which
        # was not true of the code: the cascade runs after the board branch too,
        # so a board adopter's parents were label-written by a path whose own
        # comment said it could not be reached.
        state_on_board=axis_carriage.is_board_carried("state", config, substrate_map),
        labels=parent_labels,
        substrate_map=substrate_map,
    )
    print(
        f"[cascade] bumping parent #{parent_num}: "
        f"{parent_state} → {cascade_target}"
    )
    return _gh_apply_state_label(parent_num, plan, config)


def _state_is_behind(current: str, target: str) -> bool:
    order = ["todo", "backlog", "in-progress", "review", "done"]
    try:
        return order.index(current) < order.index(target)
    except ValueError:
        return False


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
