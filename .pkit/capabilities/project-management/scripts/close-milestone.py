#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — close-milestone (verb-subject per DEC-020).

Closes a GitHub Milestone through the validated path, mirroring
`create-milestone` (the milestone verb shape) and `close-issue` (the
close/gate/audit-note pattern). The point of the wrapper is that it holds
the grant a raw `gh api -X PATCH .../milestones/<n> state=closed` lacks:
it runs the membership gate (DEC-021), the foreign-repo mutation guard
(COR-039), and routes the mutation through the shared `_lib.gh` seam
(DEC-023 host/owner pinning) — the path the `agent:project-manager`
`issue-tracker-write` deny discourages doing by hand.

Close-trigger semantics per [project-management:DEC-016-time-bound-containers]
and schemas/time-containers.yaml (READ, not re-decided here):

  * content-based — closes ONLY when every child issue is closed. An open
    child holds the close (hard refuse, exit 1) unless --force, which closes
    it with the open children left on it.
  * date-based — the date is the trigger; the Milestone closes regardless
    of how many children are still open, and its open children roll forward
    (below).
  * either — closes on whichever fires first. From its due date on, its close
    is date-triggered and rolls forward like a date-based one; before it, open
    children hold the close as they hold a content-based one.

Rollforward (#1175; the schema's rollforward_behaviour and parent_follow_rule).
A date-triggered close moves each open child to the rollforward target with
its lifecycle state kept, and leaves each closed child on the closing
Milestone as the record of what shipped. A parent issue (Feature, Umbrella,
EPIC) assigned to the closing Milestone is itself an open child while its work
goes on, so it moves with its open children while its closed children stay.
The target is the Milestone's `Rollforward target:` line, else the
next-numbered open Milestone of its category; with no candidate, or more than
one, nothing is moved or closed until the operator names it (--target).

Each move is `edit-issue <n> --milestone <target> --reason "<the close>"`, the
one writer of an issue's milestone: it posts the audit comment naming the old
Milestone, the new one and the reason (here, the close), writes the native
field, rewrites a first-line `Milestone:` ref to follow it, and refuses a move
that would shift the issue's lifecycle state. An open child whose native field
names another Milestone — only its first line still naming this one — sits in
that other Milestone and is left alone. A move closes nothing, so a
rolled-forward child never counts as closed for the closure cascade (the
schema's cascade_interaction).

The close comes first, then the moves (the schema's order). The audit line
names the target, so if a move fails the closed Milestone still says where its
open children go: a re-run reads the target back and moves the children still
on the Milestone. One already moved is no longer its child and is not moved
again, and edit-issue does not post an audit comment the failed run already
posted (it finds its own comment; the comment carries its day, so a re-run on a
later day posts a fresh one for a child whose earlier attempt failed after the
comment).

The trigger is read from the Milestone description's `Close trigger:` first
line (DEC-016). For an inherited Milestone with no marker, it is inferred
per the schema's fallback_inference: a native due date present ⇒ date-based;
none ⇒ content-based (the inference is announced).

Membership children are resolved the same way the rest of the capability
does — the union of (a) issues carrying the native GitHub Milestone field
for this milestone and (b) issues whose body carries the textual
`Milestone: [#<n>](../milestone/<n>)` ref (the form create-issue writes).
The close-trigger and the children are read through `_lib.milestone`, the
reads close-issue's closure cascade uses to say when a Milestone became
closeable, so the two cannot disagree about it.

Audit note: a GitHub Milestone has no comment thread (unlike an issue), so
the audit line is appended to the Milestone's description in the SAME PATCH
that flips state=closed — the substrate-appropriate analogue of the closing
comment the other lifecycle wrappers post. A line already there is not
appended again, so a re-run is idempotent.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/close-milestone.py 6

Or via the dispatcher (per COR-021):
  pkit project-management close-milestone 6

Exit codes:
  0  closed, with every open child rolled forward (or dry-run / already-closed
     noop)
  1  membership refusal / session refusal / open children holding a content
     close / no single rollforward target
  2  usage error (milestone not found; --target matches no open milestone, or
     is given to a close that rolls nothing forward)
  3  gh failure
  4  closed, but an open child did not move — re-run to finish the rollforward
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, session_guard
from _lib.gh import gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.milestone import (
    Milestone,
    date_trigger_fired,
    due_date,
    fetch_milestone,
    list_milestone_children,
    list_open_milestones,
    native_milestone_matches,
    next_numbered_milestones,
    parse_rollforward_target,
    resolve_close_trigger,
    resolve_milestone,
)

# The audit marker written into the Milestone description on close.
_AUDIT_MARKER = "Closed via `pkit project-management close-milestone`"

# The audit line's rollforward clause, which a re-run reads the target back from.
_ROLLED_FORWARD = re.compile(r"\d+ rolled forward to #(?P<target>\d+)")

# The Milestone closed, but an open child did not move.
EXIT_ROLLFORWARD_INCOMPLETE = 4


@dataclass(frozen=True)
class RollforwardTarget:
    """Where a date-triggered close moves the open children, and how it was
    chosen (for the plan's output)."""

    milestone: Milestone
    source: str


@dataclass(frozen=True)
class RollforwardPlan:
    """The moves a date-triggered close makes.

    moves — the open children that move to the target: those whose native
            Milestone field names the closing Milestone, the target (a move a
            failed run left half done) or none.
    left  — open children whose native field names another Milestone; they sit
            in that one and are left alone.
    """

    target: RollforwardTarget
    moves: tuple[dict, ...]
    left: tuple[dict, ...]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Close a GitHub Milestone through the validated path. Respects "
            "the milestone's close-trigger (content-based / date-based / "
            "either) per time-containers.yaml; a date-triggered close rolls the "
            "open children forward to the next milestone. Appends an audit "
            "line, and supports --dry-run."
        ),
    )
    parser.add_argument(
        "milestone",
        help="Milestone NUMBER (e.g. 6) or exact TITLE to close.",
    )
    parser.add_argument(
        "--target",
        default=None,
        metavar="M",
        help=(
            "The OPEN milestone (number or exact title) a date-triggered close "
            "rolls the open children forward to, in place of the milestone's "
            "`Rollforward target:` line or the next-numbered open milestone of "
            "its category. Needed when there is no candidate, or more than one."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Close a content-based milestone, or an either one before its due "
            "date, despite open child issues. They stay on the closed milestone: "
            "only a date-triggered close rolls children forward."
        ),
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
        help="Print the plan, every rollforward move included; do not invoke gh.",
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
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("close-milestone", capability_root=capability_root):
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

    # Resolve the milestone NUMBER. A numeric arg is used directly (so a
    # milestone the open-only resolver would miss still resolves); a title arg
    # goes through the shared resolver (open milestones, number-or-title).
    number = _resolve_number(args.milestone, config)
    if number is None:
        return 2

    milestone = fetch_milestone(number, config)
    if milestone is None:
        return 2

    title = str(milestone.get("title", ""))
    state = str(milestone.get("state", "")).lower()
    description = str(milestone.get("description") or "")
    due_on = milestone.get("due_on")

    close_trigger, inferred = resolve_close_trigger(description, due_on)

    print(f"close-milestone: #{number}")
    print(f"  title:         {title}")
    print(f"  current state: {state}")
    print(f"  close_trigger: {close_trigger}" + (" (inferred)" if inferred else ""))

    # A Milestone this command closed with a rollforward a failure cut short
    # records its target; a re-run finishes that rollforward. Any other closed
    # Milestone is left as it is.
    recorded = _recorded_target(description) if state == "closed" else None
    if state == "closed" and recorded is None:
        print("\n[noop] milestone already closed.")
        return 0

    issue_types = _read_yaml(capability_root / "schemas" / "issue-types.yaml", yaml_loader)
    # Kind-driven title prefixes ([Bug]/[Docs]/[Test]/[Refactor]/[Chore]) live in
    # classification.yaml; without it a kind-prefixed Task reads as unrecognised.
    classification = _read_yaml(capability_root / "schemas" / "classification.yaml", yaml_loader)

    children = list_milestone_children(number, title, config, issue_types, classification)
    if children is None:
        return 3
    open_children = [c for c in children if c["state"] != "closed"]

    print(f"  children:      {len(children)} ({len(open_children)} open)")
    for child in open_children:
        print(f"    - {_child_label(child)} (open)")

    if recorded is not None:
        return _finish_rollforward(args, number, title, recorded, open_children, config)

    date_triggered = date_trigger_fired(close_trigger, due_on, _today())
    if args.target is not None and not date_triggered:
        print(
            f"error: --target names where a date-triggered close rolls the open "
            f"children forward; this {_trigger_phrase(close_trigger, due_on)} "
            "close is not date-triggered, so it rolls nothing forward.",
            file=sys.stderr,
        )
        return 2

    decision = _decide_close(bool(open_children), force=args.force, date_triggered=date_triggered)
    if not decision.proceed:
        print(
            f"\n[refused] {_trigger_phrase(close_trigger, due_on)} milestone with "
            "open child issue(s); close is held until every child closes.",
            file=sys.stderr,
        )
        print(
            "  → close each open child first, or pass --force to close anyway "
            "(the open children stay on the closed milestone: only a "
            "date-triggered close rolls them forward).",
            file=sys.stderr,
        )
        return decision.exit_code

    plan: RollforwardPlan | None = None
    if decision.rolls_forward:
        target = _choose_target(args.target, description, number, title, config)
        if isinstance(target, int):
            return target
        plan = _plan_rollforward(open_children, number, title, target)
        _print_plan(plan, number)
    elif decision.leaves_open_children:
        print(
            f"\n[warn] forced {close_trigger} close with {len(open_children)} open "
            "child issue(s). They stay assigned to this milestone: only a "
            "date-triggered close rolls children forward. Move each open child "
            "above by hand: `pkit project-management edit-issue <n> --milestone "
            '<next> --reason "<why>"`.',
            file=sys.stderr,
        )

    closed_count = len(children) - len(open_children)
    left_open = len(plan.left) if plan is not None else len(open_children)
    new_description = _compose_close_description(
        description,
        close_trigger=close_trigger,
        closed_count=closed_count,
        plan=plan,
        left_open=left_open,
    )

    if args.dry_run:
        audit = _audit_line(close_trigger, closed_count, plan=plan, left_open=left_open)
        print("\n[dry-run] gh would be invoked; nothing written.")
        print("  would PATCH state=closed and append the audit line:")
        print(f"    {audit}")
        if plan is not None and plan.moves:
            print(
                f"  would then make each move above: `edit-issue <n> --milestone "
                f'{plan.target.milestone.number} --reason "{_rollforward_reason(number)}"`'
            )
        return 0

    question = "Close this milestone? [y/N] "
    if plan is not None and plan.moves:
        question = (
            f"Close this milestone and roll {len(plan.moves)} open child issue(s) "
            f"forward to {_milestone_label(plan.target.milestone)}? [y/N] "
        )
    if not _confirmed(args, question):
        return 0

    if not _gh_close_milestone(number, new_description, config):
        return 3

    print(f"\n[ok] closed milestone #{number} ({close_trigger}).")
    if plan is None or not plan.moves:
        return 0
    return _roll_forward(plan, number, args)


# ---- close decision (pure policy) -----------------------------------


@dataclass(frozen=True)
class CloseDecision:
    """The trigger-policy verdict for a close attempt (confirmation aside).

    proceed              — go ahead and close (main still applies the --yes /
                           interactive confirmation gate).
    exit_code            — exit code when NOT proceeding (a refusal).
    rolls_forward        — the close is date-triggered and has open children:
                           they move to the rollforward target.
    leaves_open_children — a forced content close: the open children stay on
                           the closed Milestone.
    """

    proceed: bool
    exit_code: int = 0
    rolls_forward: bool = False
    leaves_open_children: bool = False


def _decide_close(has_open_children: bool, *, force: bool, date_triggered: bool) -> CloseDecision:
    """Decide whether to close, and what becomes of the open children.

    No open children ⇒ always proceed (a clean close for any trigger).
    Open children:
      * a date-triggered close (date-based, or either from its due date) —
        proceed, rolling them forward;
      * otherwise (content-based, or either before its due date) — hard refuse
        (exit 1) unless --force, which closes with them left in place.
    """
    if not has_open_children:
        return CloseDecision(proceed=True)
    if date_triggered:
        return CloseDecision(proceed=True, rolls_forward=True)
    if force:
        return CloseDecision(proceed=True, leaves_open_children=True)
    return CloseDecision(proceed=False, exit_code=1)


def _trigger_phrase(close_trigger: str, due_on: object) -> str:
    """The close-trigger as a refusal names it; an `either` one with its date."""
    if close_trigger != "either":
        return close_trigger
    due = due_date(due_on)
    return f"either (due {due.isoformat()})" if due else "either (no due date)"


# ---- rollforward ----------------------------------------------------


def _choose_target(
    arg: str | None, description: str, number: int, title: str, config: dict
) -> RollforwardTarget | int:
    """The rollforward target, or the exit code to stop with.

    --target wins; else the Milestone's `Rollforward target:` line; else the
    next-numbered open Milestone of its category (DEC-016). No candidate, or more
    than one, is refused before anything is written — the operator names it.
    """
    if arg is not None:
        named = resolve_milestone(arg, config)
        if named is None:
            print(
                f"error: --target {arg!r} did not match any OPEN milestone "
                "(tried as number, then as title).",
                file=sys.stderr,
            )
            return 2
        if named.number == number:
            print(
                "error: --target names the milestone being closed; name the one "
                "its open children move to.",
                file=sys.stderr,
            )
            return 2
        return RollforwardTarget(named, "--target")

    declared = parse_rollforward_target(description)
    if declared is not None:
        named = resolve_milestone(declared, config)
        if named is None or named.number == number:
            _refuse_target(
                number,
                f"its `Rollforward target:` line names {declared!r}, which is not "
                "another OPEN milestone",
            )
            return 1
        return RollforwardTarget(named, "its `Rollforward target:` line")

    open_milestones = list_open_milestones(config)
    if open_milestones is None:
        print("error: could not list the open milestones (gh failure).", file=sys.stderr)
        return 3
    candidates = next_numbered_milestones(
        title, open_milestones, config.get("milestone_categories")
    )
    if len(candidates) == 1:
        return RollforwardTarget(candidates[0], "the next-numbered open milestone of its category")
    if candidates:
        why = "more than one open milestone could come next: " + ", ".join(
            _milestone_label(c) for c in candidates
        )
    else:
        why = (
            "no open milestone of its category is numbered after it (or its title "
            "fits no declared `milestone_categories:` format)"
        )
    _refuse_target(number, why)
    return 1


def _refuse_target(number: int, why: str) -> None:
    print(
        f"\n[refused] no rollforward target for #{number}: {why}. Nothing was "
        "moved or closed.\n"
        f"  → name it: `pkit project-management close-milestone {number} --target "
        "<number|title>`.",
        file=sys.stderr,
    )


def _plan_rollforward(
    open_children: list[dict], number: int, title: str, target: RollforwardTarget
) -> RollforwardPlan:
    """Split the open children into the ones that move and the ones left alone.

    A child moves when its native Milestone field names the closing Milestone,
    none, or the target (a move a failed run left half done: the native field
    moved, the first line did not). One whose native field names another
    Milestone sits in that one — only its first line still names this one — so
    moving it would undo that assignment; it is left alone.
    """
    moves: list[dict] = []
    left: list[dict] = []
    for child in open_children:
        native = child.get("milestone")
        if (
            native is None
            or native_milestone_matches(native, number, title)
            or native_milestone_matches(native, target.milestone.number, target.milestone.title)
        ):
            moves.append(child)
        else:
            left.append(child)
    return RollforwardPlan(target=target, moves=tuple(moves), left=tuple(left))


def _print_plan(plan: RollforwardPlan, number: int) -> None:
    target = plan.target.milestone
    print(f"  rollforward:   → {_milestone_label(target)} ({plan.target.source})")
    for child in plan.moves:
        print(f"    - {_child_label(child)}: #{number} → #{target.number}")
    for child in plan.left:
        print(
            f"    · {_child_label(child)}: left alone — its native Milestone field "
            f"names {_native_label(child.get('milestone'))}"
        )


def _roll_forward(plan: RollforwardPlan, number: int, args: argparse.Namespace) -> int:
    """Move each planned child through `edit-issue --milestone`, then report.

    Every move is attempted, so one failure does not hold the rest; a failure
    leaves the closed Milestone naming the target, for a re-run to finish.
    """
    target = plan.target.milestone
    reason = _rollforward_reason(number)
    failed: list[int] = []
    for child in plan.moves:
        print(f"\n[rollforward] #{child['number']} → #{target.number}")
        exit_code = _run_edit_issue(
            child["number"],
            target.number,
            reason,
            capability_root=args.capability_root,
            allow_foreign_repo=args.allow_foreign_repo,
        )
        if exit_code != 0:
            failed.append(child["number"])
    moved = len(plan.moves) - len(failed)
    if failed:
        print(
            f"\n[incomplete] {moved} of {len(plan.moves)} open child issue(s) rolled "
            f"forward to {_milestone_label(target)}; "
            f"{', '.join(f'#{n}' for n in failed)} did not move (see edit-issue's "
            "output above). The milestone is closed and its audit line names the "
            "target: fix what stopped them, then re-run "
            f"`pkit project-management close-milestone {number}` to move the rest.",
            file=sys.stderr,
        )
        return EXIT_ROLLFORWARD_INCOMPLETE
    print(f"\n[ok] rolled {moved} open child issue(s) forward to {_milestone_label(target)}.")
    return 0


def _finish_rollforward(
    args: argparse.Namespace,
    number: int,
    title: str,
    recorded: int,
    open_children: list[dict],
    config: dict,
) -> int:
    """Re-run on a Milestone this command closed with a rollforward: move the
    open children still on it to the target its audit line recorded."""
    if not open_children:
        print(f"\n[noop] milestone already closed; its rollforward to #{recorded} is complete.")
        return 0

    target = resolve_milestone(str(recorded), config)
    if target is None:
        print(
            f"error: #{recorded}, the rollforward target this milestone's close "
            "recorded, is not an open milestone. Move its open children by hand: "
            '`pkit project-management edit-issue <n> --milestone <M> --reason "<why>"`.',
            file=sys.stderr,
        )
        return 1
    if args.target is not None:
        named = resolve_milestone(args.target, config)
        if named is None or named.number != target.number:
            print(
                f"error: this milestone closed rolling forward to #{recorded}; a "
                "re-run finishes that rollforward, so --target cannot name another.",
                file=sys.stderr,
            )
            return 2

    print(
        f"\n[resume] milestone already closed; finishing its rollforward to "
        f"{_milestone_label(target)}."
    )
    plan = _plan_rollforward(
        open_children, number, title, RollforwardTarget(target, "recorded by its close")
    )
    _print_plan(plan, number)
    if not plan.moves:
        return 0
    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0
    question = (
        f"Roll {len(plan.moves)} open child issue(s) forward to {_milestone_label(target)}? [y/N] "
    )
    if not _confirmed(args, question):
        return 0
    return _roll_forward(plan, number, args)


def _rollforward_reason(number: int) -> str:
    """The reason each move's audit comment carries: the Milestone the child
    leaves and the close that moved it. It names that Milestone itself, since the
    comment's from-side is the native field, which a child counted through its
    first line alone does not carry.

    Free of the date, so a re-run passes edit-issue the same reason and the
    comment the failed run posted is found rather than posted again.
    """
    return (
        f"rolled forward from #{number} when "
        f"`pkit project-management close-milestone {number}` closed it"
    )


def _recorded_target(description: str) -> int | None:
    """The rollforward target this command's last audit line on the Milestone
    names, or None — closed by hand, by an earlier version of this command, or
    with nothing rolled forward."""
    for line in reversed(description.splitlines()):
        if _AUDIT_MARKER in line:
            recorded = _ROLLED_FORWARD.search(line)
            return int(recorded.group("target")) if recorded else None
    return None


def _run_edit_issue(
    issue_number: int,
    target: int,
    reason: str,
    *,
    capability_root: Path | None,
    allow_foreign_repo: bool,
) -> int:
    """Move one issue with `edit-issue --milestone`, the one writer of an issue's
    milestone, non-interactively (`--yes`); its output streams into this run's.
    Returns its exit code."""
    cmd = [
        sys.executable,
        str(_HERE / "edit-issue.py"),
        str(issue_number),
        "--milestone",
        str(target),
        "--reason",
        reason,
        "--yes",
    ]
    if allow_foreign_repo:
        cmd.append("--allow-foreign-repo")
    if capability_root is not None:
        cmd += ["--capability-root", str(capability_root)]
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        return subprocess.run(cmd, check=False).returncode
    except OSError as exc:
        print(f"error: could not run edit-issue for #{issue_number}: {exc}", file=sys.stderr)
        return 3


# ---- audit note -----------------------------------------------------


def _audit_line(
    close_trigger: str,
    closed_count: int,
    *,
    plan: RollforwardPlan | None = None,
    left_open: int = 0,
) -> str:
    """Compose the one-line audit note appended to the Milestone description.

    It counts the children rolled forward and names their target — the record a
    re-run finishes an interrupted rollforward from — and counts as still open,
    not rolled forward, any open child the close leaves on the Milestone.
    """
    clauses = [f"trigger: {close_trigger}", f"{closed_count} child issue(s) closed"]
    if plan is not None and plan.moves:
        clauses.append(
            f"{len(plan.moves)} rolled forward to {_milestone_label(plan.target.milestone)}"
        )
    if left_open:
        clauses.append(f"{left_open} still open, not rolled forward")
    return f"{_AUDIT_MARKER} on {_today().isoformat()} ({'; '.join(clauses)})."


def _compose_close_description(
    description: str,
    *,
    close_trigger: str,
    closed_count: int,
    plan: RollforwardPlan | None = None,
    left_open: int = 0,
) -> str:
    """Append the audit line to the description; idempotent on re-run.

    A Milestone has no comment thread, so the audit note lives in the
    description (written in the same PATCH that flips state=closed). A line
    already there is not appended again, so a re-run does not stack notes; a
    Milestone reopened and closed again records its new close.
    """
    line = _audit_line(close_trigger, closed_count, plan=plan, left_open=left_open)
    if line in description.splitlines():
        return description
    if description.strip():
        return description.rstrip() + "\n\n" + line
    return line


def _today() -> _dt.date:
    return _dt.date.today()


# ---- labels -----------------------------------------------------------


def _child_label(child: dict) -> str:
    return f"#{child['number']} [{child.get('type') or 'issue'}] {child['title']}"


def _milestone_label(milestone: Milestone) -> str:
    return f"#{milestone.number} {milestone.title}".rstrip()


def _native_label(native: object) -> str:
    if not isinstance(native, dict):
        return "no milestone"
    number = native.get("number")
    title = str(native.get("title") or "")
    return f"#{number} {title}".rstrip() if isinstance(number, int) else repr(title)


# ---- gh helpers -----------------------------------------------------


def _resolve_number(arg: str, config: dict) -> int | None:
    """Resolve the milestone argument to a NUMBER (numeric direct, else title)."""
    if arg.strip().lstrip("-").isdigit():
        return int(arg)
    resolved = resolve_milestone(arg, config)
    if resolved is None:
        print(
            f"error: no open milestone matches {arg!r}. Pass the milestone "
            "number, or the exact title of an open milestone.",
            file=sys.stderr,
        )
        return None
    return resolved.number


def _gh_close_milestone(number: int, description: str, config: dict) -> bool:
    """PATCH the milestone to state=closed (+ audit description) via `gh_run`.

    Routes the mutation through the shared `_lib.gh` seam — the validated path
    that pins the adopter's host/owner (DEC-023) and that the wrapper's grant
    covers, rather than a raw `gh api` the agent deny discourages.
    """
    args = [
        "gh",
        "api",
        "-X",
        "PATCH",
        f"repos/{{owner}}/{{repo}}/milestones/{number}",
        "-f",
        "state=closed",
        "-f",
        f"description={description}",
    ]
    try:
        proc = gh_run(args, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: gh failed closing milestone #{number} "
            f"(exit {proc.returncode}).\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


# ---- I/O helpers ----------------------------------------------------


def _confirmed(args: argparse.Namespace, question: str) -> bool:
    """The --yes / interactive confirmation gate; a non-interactive run proceeds."""
    if args.yes or not sys.stdin.isatty():
        return True
    if input(question).strip().lower() in ("y", "yes"):
        return True
    print("aborted.", file=sys.stderr)
    return False


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
