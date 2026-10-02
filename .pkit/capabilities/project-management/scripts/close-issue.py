#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — close-issue (verb-subject per DEC-020).

Closes a GitHub issue via either path declared in workflow.yaml's
`closure_triggers`:

  * `--mode=wont-do` (default when --reason supplied or when caller is
    explicit) — posts a closing comment with the reason, verifies the
    checkbox close-gate per DEC-007, then closes via `gh issue close`.
  * `--mode=pr-merge` — issue closure was triggered by GitHub's
    `Closes #N` keyword. The script runs the cascade pass on parents
    after the fact; it does not itself close the issue.
    With `--pr <M>` it DOES close an open leaf (a Task) whose work landed in
    merged PR M without the PR naming it: PR M is verified merged, the
    DEC-007 checkbox close-gate runs, the reference is posted as a comment,
    and the issue closes as completed before the cascade pass (#1049).
  * `--mode=cascade-eligibility-close` — closes a container (epic/feature/
    umbrella) once every child is closed AND its own checkboxes are ticked
    (the DEC-007 gate is non-skippable here). Implements the
    `cascade-eligibility-close` trigger this script previously only reported.
    Closes via `gh issue close --reason completed`.

All three paths reconcile the issue's ``state:*`` labels after closing: any
non-terminal label (``state:todo``, ``state:backlog``, ``state:in-progress``,
``state:review``) is removed and ``state:done`` is ensured.  The reconcile
logic is shared with ``move-issue`` via ``_lib.labels.reconcile_state_labels_to_done``
so there is no duplicated label-mutation code.

After closing, every path runs the closure cascade (DEC-006), which reports and
never closes: each parent issue the body's first line names is checked for
close eligibility, and so is each Milestone the issue sits in (its native
Milestone field, or a ``Milestone: [#<n>](../milestone/<n>)`` body ref). A
content-based (or ``either``) Milestone whose every child issue is closed is
reported as eligible, with the ``close-milestone`` command that closes it
(#414); a date-based one closes on its date, so its children closing makes
nothing eligible.

Each close is a governed move to done, recorded with the process engine through
the path ``move-issue`` records its moves through (``_lib.move_journal``,
``pkit process move --from``; #1231): after the close and its label reconcile,
one move from the state the issue held before the close, with the close mode
as the entry's reason. That state is read from the issue as fetched at the
start, before anything is written (``lifecycle_inference.state_before_close``):
its state label, else its milestone, else Todo — read as if it were open, so
an issue GitHub closed when a pull request merged reads where the merge found
it. An issue whose label already says done was moved there by whoever wrote
the label — ``move-issue``, or an earlier run of this script — and is not
recorded again, so a re-run adds nothing. Whether the move is recorded is the
engine's: it appends to the journal where the project keeps one and records
nothing where it does not. A move the workflow does not declare for the issue's
type — a Task closed from In Progress, say — is not handed to the engine, which
does not read a transition's ``applies_to``; it, and a move the engine refuses
because its gate does not pass, are warned about as a direct move's refusal
is, and the close stands.

The ``state`` write is RESOLVED through the substrate-map seam (ADR-026
sole-constructor + fail-closed), the same as ``move-issue``: greenfield (no
``substrate-map.yaml``) writes the kit's own ``state:done``; a present map that
binds ``state`` to a ``derive`` predicate (or marks it ``unsupported`` / omits
it) writes NO kit ``state:*`` label — the open/closed substrate carries terminal
state, so closing the issue *is* the state write (ADR-026 §5). The map is loaded
once in :func:`main` and threaded into every reconcile call.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/close-issue.py 42 --reason "superseded by #99"

Or via the dispatcher (per COR-021):
  pkit project-management close-issue 42 --reason "..."

Exit codes:
  0  closed (or cascade reported)
  1  membership refusal / authorisation refusal / checkbox close-gate refusal /
     `--pr` names a PR that is not merged
  2  usage error (issue or PR not found; mode contradicts state; `--pr` outside
     pr-merge mode or on a non-leaf)
  3  gh failure
"""  # noqa: E501 — a usage line is a command, kept whole

from __future__ import annotations

import argparse
import json
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
    axis_labels,
    body_parent_ref,
    bootstrap_gate,
    containment,
    engine_said,
    session_guard,
)
from _lib import lifecycle_inference as infer

# DEC-007's checkbox close-gate — the ONE implementation (`_lib.checkbox_gate`),
# shared with done-work, merge-pr and the engine's gate-checkboxes-ticked
# predicate. Aliased to the local names this script has always used.
from _lib.checkbox_gate import refusal_message as _checkbox_refusal
from _lib.checkbox_gate import unticked_boxes as _unticked_boxes
from _lib.comment import post_audit_once
from _lib.gh import gh_get_issue, gh_get_pr, gh_run, load_adopter_config
from _lib.hooks import fire_hooks
from _lib.labels import reconcile_state_labels_to_done
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.milestone import (
    CONTENT_TRIGGERS,
    fetch_milestone,
    issue_milestones,
    list_milestone_children,
    resolve_close_trigger,
)
from _lib.move_journal import (
    PR_MERGE_CLOSE,
    PROCESS_ADDRESS,
    journal_move,
    pr_merge_close_reason,
    report_unrecorded,
)
from _lib.structural_type import infer_structural_type

VALID_MODES = ("wont-do", "pr-merge", "cascade-eligibility-close")
DEFAULT_MODE = "wont-do"

# The lifecycle state every close moves an issue to.
DONE_STATE = "done"

# The writer name in the idempotency key of the `--pr` close comment, so a
# retry after a failed close does not post the reference twice (`_lib.audit`).
PR_MERGE_CLOSE_WRITER = "close-issue-pr-merge"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Close a GitHub issue per the methodology's closure rules. "
            "Default mode is wont-do (explicit gesture with reason + close-"
            "gate check); pr-merge mode is the post-close cascade hook."
        ),
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number to close.",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default=DEFAULT_MODE,
        help=(
            f"Closure mode. Default: {DEFAULT_MODE}. "
            "`wont-do` posts a closing comment + closes; "
            "`pr-merge` is the cascade-only hook after GitHub-native close "
            "(with --pr, it closes an open leaf itself); "
            "`cascade-eligibility-close` closes a container (epic/feature/"
            "umbrella) once all children are closed and its own checkboxes "
            "are ticked (non-skippable gate)."
        ),
    )
    parser.add_argument(
        "--pr",
        type=int,
        default=None,
        metavar="M",
        help=(
            "pr-merge mode only: the merged PR that completed this issue "
            "without naming it in a `Closes #N` line. An OPEN leaf (a Task) is "
            "closed as completed — PR M is verified merged, the DEC-007 "
            "checkbox close-gate runs, the reference is posted as a comment, "
            "then the closure cascade runs. Without --pr, pr-merge mode only "
            "reconciles labels after GitHub's own close."
        ),
    )
    parser.add_argument(
        "--reason",
        default=None,
        help=("Closing reason recorded in the closing comment. Required in wont-do mode."),
    )
    parser.add_argument(
        "--skip-checkbox-gate",
        action="store_true",
        help=(
            "Skip the DEC-007 checkbox close-gate. Discouraged; only use "
            "when you have just removed all open boxes by hand."
        ),
    )
    parser.add_argument(
        "--no-cascade",
        action="store_true",
        help="Skip the closure-cascade walk on parent issues.",
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

    if args.pr is not None and args.mode != "pr-merge":
        print(
            f"error: --pr applies to --mode=pr-merge only (got --mode={args.mode}).",
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
    if not bootstrap_gate.enforce("close-issue", capability_root=capability_root):
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

    issue_types = _read_yaml(capability_root / "schemas" / "issue-types.yaml", yaml_loader)
    # Kind-driven title prefixes ([Bug]/[Docs]/[Test]/[Refactor]/[Chore]) live in
    # classification.yaml; without it a kind-prefixed Task reads as unrecognised.
    classification = _read_yaml(capability_root / "schemas" / "classification.yaml", yaml_loader)

    # The adopter's optional substrate-map (ADR-026): None ⇒ greenfield (state
    # is a `state:*` label); a present map may bind `state` to a `derive`
    # predicate (or mark it unsupported / omit it) ⇒ the kit writes NO `state:*`
    # label on close (the open/closed substrate carries terminal state). Loaded
    # once here and threaded into every reconcile call below (RF-1, #265).
    substrate_map = axis_labels.load_substrate_map(capability_root)

    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    title = str(issue.get("title", ""))
    body = str(issue.get("body") or "")
    state = str(issue.get("state", "")).lower()
    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    structural_type = infer_structural_type(title, issue_types, classification=classification)
    # The move to done each path below records once it has closed the issue
    # (#1231), read before anything is written.
    close_move = _CloseMove.read(
        args.issue_number,
        issue,
        labels,
        structural_type,
        workflow=_read_yaml(capability_root / "schemas" / "workflow.yaml", yaml_loader),
        substrate_map=substrate_map,
        actor=invoker.github_login,
    )

    print(f"close-issue: #{args.issue_number}")
    print(f"  title:        {title}")
    print(f"  type:         {structural_type or '<unrecognised prefix>'}")
    print(f"  current state: {state}")
    print(f"  mode:         {args.mode}")

    if args.mode == "wont-do":
        if state == "closed":
            print("\n[noop] issue already closed.")
            return 0
        if not args.reason:
            print(
                "\nerror: --reason is required in wont-do mode.",
                file=sys.stderr,
            )
            return 2

        # Checkbox close-gate per DEC-007.
        unticked = [] if args.skip_checkbox_gate else _unticked_boxes(body)
        if unticked:
            print(
                "\n"
                + _checkbox_refusal(
                    unticked,
                    remedy=(
                        "tick or remove each unticked checkbox before closing, "
                        "or pass --skip-checkbox-gate (discouraged)."
                    ),
                ),
                file=sys.stderr,
            )
            return 1

        print(f"\nreason: {args.reason}")
        if args.dry_run:
            print("\n[dry-run] gh would be invoked; nothing written.")
            return 0
        if not args.yes and sys.stdin.isatty():
            reply = input("Proceed? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("aborted.", file=sys.stderr)
                return 0

        comment_body = (
            f"[wont-do close] {args.reason}\n\n"
            f"Closed via `pkit project-management close-issue` "
            f"(per [project-management:DEC-006-state-machine-and-cascade])."
        )
        if not _gh_comment(args.issue_number, comment_body, config):
            return 3
        if not _gh_close_issue(args.issue_number, reason="not planned", config=config):
            return 3
        # Reconcile state:* labels — remove any non-terminal label and ensure
        # state:done.  Shared routine from _lib.labels (same logic as
        # move-issue's reconcile path) so there is no duplicated label logic.
        # Map-aware (RF-1): under a present derive/unsupported `state` map this
        # writes no kit `state:*` label (the open/closed substrate carries it).
        if not reconcile_state_labels_to_done(
            args.issue_number,
            labels,
            config,
            gh_run=gh_run,
            substrate_map=substrate_map,
        ):
            return 3
        close_move.record(f"wont-do close: {args.reason}")
        print(f"\n[ok] closed #{args.issue_number} (wont-do).")

    elif args.mode == "pr-merge" and args.pr is not None and state != "closed":
        # The work landed in a merged PR that did not name this issue, so
        # GitHub's `Closes #N` never closed it: close it here, as completed.
        rc = _close_leaf_through_pr(
            args,
            structural_type=structural_type,
            body=body,
            labels=labels,
            config=config,
            substrate_map=substrate_map,
            close_move=close_move,
        )
        if rc is not None:
            return rc

    elif args.mode == "pr-merge":
        # In pr-merge mode the issue is expected to be already-closed
        # via GitHub's Closes #N. The script's job is the cascade pass
        # plus label reconciliation (GitHub's auto-close does not touch
        # state:* labels).
        if args.pr is not None:
            print(
                f"\n[noop] #{args.issue_number} is already closed; --pr is not "
                "needed — reconciling labels only."
            )
        elif state != "closed":
            print(
                "\n[warn] pr-merge mode but issue is still open. "
                "GitHub's Closes #N should have closed it on PR merge. "
                "Re-check the merged PR's body for `Closes #N`; if the PR did "
                "not name this issue, re-run with --pr <M> to close it through "
                "that PR.",
                file=sys.stderr,
            )
        # Reconcile state:* labels regardless of open/closed state warning
        # above — the caller explicitly indicated a PR-merge close, so the
        # terminal label must be correct.
        if not args.dry_run:
            if not reconcile_state_labels_to_done(
                args.issue_number,
                labels,
                config,
                gh_run=gh_run,
                substrate_map=substrate_map,
            ):
                return 3
            # GitHub closed the issue and wrote no label: the move to done is
            # recorded here, from where the merge found it — unless its label
            # already says done (done-work's move-issue wrote it, or a re-run).
            close_move.record(
                pr_merge_close_reason(args.pr, closed_by_merge=True)
                if args.pr is not None
                else PR_MERGE_CLOSE
            )
        print(f"\n[ok] noted pr-merge close for #{args.issue_number}.")

    elif args.mode == "cascade-eligibility-close":
        # Close a container (epic/feature/umbrella) that is cascade-eligible per
        # DEC-006 + workflow.yaml closure_triggers[cascade-eligibility-close]:
        # EVERY child is closed AND the container's own checkboxes are ticked.
        # The checkbox gate is a DEC-007 hard-reject here and is NOT skippable
        # (unlike wont-do) — a container is "done" only when its work is
        # genuinely complete. Closes with reason=completed.
        if structural_type not in ("epic", "feature", "umbrella"):
            print(
                "\nerror: cascade-eligibility-close applies to container issues "
                "(epic/feature/umbrella); "
                f"#{args.issue_number} is "
                f"{structural_type or 'an unrecognised type'}. "
                "Use --mode=wont-do, or close a leaf via its PR (Closes #N).",
                file=sys.stderr,
            )
            return 2
        if state == "closed":
            print("\n[noop] issue already closed.")
            return 0

        # Eligibility half 1 — own checkboxes ticked (DEC-007, NOT skippable here).
        unticked = _unticked_boxes(body)
        if unticked:
            print(
                "\n"
                + _checkbox_refusal(
                    unticked,
                    scope="cascade-eligibility",
                    remedy=(
                        "a container closes only when its own checkboxes are "
                        "all ticked. This gate is not skippable in "
                        "cascade-eligibility-close."
                    ),
                ),
                file=sys.stderr,
            )
            return 1

        # Eligibility half 2 — every child closed (the CHILDREN-HALF of the
        # conjunction). DEC-034 / DEC-033 D5: the wrapper no longer folds this
        # itself — it reads the process ENGINE's shared cascade resolution
        # (`pkit process cascade`), which folds the issue-lifecycle `all`-over-
        # `done` declaration in workflow.yaml. The close rule stays the
        # CONJUNCTION of (half 1) the checkbox gate above AND (half 2) this fold.
        #
        #   opened == True   -> every child reached `done` (or childless via
        #                       on_empty: satisfied) -> children-half satisfied.
        #   opened == False, indeterminate == False
        #                    -> a determinate "not yet": an open child holds the
        #                       fold (matches "open child blocks eligibility",
        #                       DEC-016 roll-forward included) -> refuse.
        #   indeterminate == True
        #                    -> the fold could not be resolved (a reachable engine
        #                       that could not fold: broken members/membership read
        #                       or an unresolved member); HOLD fail-closed -> refuse
        #                       (never fail-open), per COR-037 precedence.
        #   fold is None     -> `pkit` itself was unreachable (could not even invoke
        #                       the engine); also HOLD fail-closed -> refuse.
        # Both indeterminate and None are fail-closed holds; they differ only in
        # exit code (1 = engine reachable but refused/held; 3 = engine unreachable),
        # so callers/CI can tell a policy refusal from an environment failure. Keep
        # the 3-vs-1 split: it is a deliberate two-failure-surface contract, not noise.
        fold = _engine_cascade_fold(args.issue_number)
        if fold is None or fold.get("indeterminate"):
            reason = fold.get("reason") if isinstance(fold, dict) else None
            print(
                "\n[refused] could not resolve the children-half of cascade "
                "eligibility (held fail-closed):",
                file=sys.stderr,
            )
            print(
                f"  → {reason or 'the process engine could not fold the children.'}",
                file=sys.stderr,
            )
            # What a predicate the fold could not evaluate said, as the engine
            # reports it (`stderr_tail`), under the reason.
            said = fold.get("stderr_tail") if isinstance(fold, dict) else None
            for line in engine_said.said_lines(said, "    "):
                print(line, file=sys.stderr)
            print(
                "  → re-run once `gh` is reachable and every child's state is "
                "readable; the container holds until the fold resolves.",
                file=sys.stderr,
            )
            return 3 if fold is None else 1
        if not fold.get("opened"):
            print("\n[refused] not cascade-eligible — not every child has closed:")
            print(f"  · fold: {fold.get('reason', '')}")
            # Diagnostic colour only (the engine fold above is the DECISION): list
            # the still-open children so the user knows what to close.
            open_children = _find_open_children(args.issue_number, config)
            for n in open_children or []:
                print(f"  - #{n}")
            print(
                "\n  → close every child first; the container becomes eligible "
                "when the last child closes.",
                file=sys.stderr,
            )
            return 1

        if args.dry_run:
            print(
                "\n[dry-run] eligible (all children closed, checkboxes ticked); "
                "gh would close with --reason completed."
            )
            return 0
        if not args.yes and sys.stdin.isatty():
            reply = input("Close cascade-eligible container? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("aborted.", file=sys.stderr)
                return 0

        comment_body = (
            "[cascade-eligibility close] all children closed and the container's "
            "checkboxes are complete.\n\n"
            "Closed via `pkit project-management close-issue "
            "--mode=cascade-eligibility-close` "
            "(per [project-management:DEC-006-state-machine-and-cascade])."
        )
        if not _gh_comment(args.issue_number, comment_body, config):
            return 3
        if not _gh_close_issue(args.issue_number, reason="completed", config=config):
            return 3
        if not reconcile_state_labels_to_done(
            args.issue_number,
            labels,
            config,
            gh_run=gh_run,
            substrate_map=substrate_map,
        ):
            return 3
        close_move.record("cascade-eligibility close: every child closed and every checkbox ticked")
        print(f"\n[ok] closed #{args.issue_number} (cascade-eligibility, completed).")

    # Closure cascade — semi-automatic per DEC-006: it reports eligibility and
    # closes nothing, over the parent issues and the Milestones alike.
    if not args.no_cascade:
        parent_num = body_parent_ref.parent_issue(body, structural_type, issue_types)
        unrecognised = body_parent_ref.read_first_line(body, structural_type, issue_types).note
        if parent_num is not None:
            print(f"\n[cascade] parents to check for eligibility: #{parent_num}")
            _check_parent_eligibility(parent_num, config)
        elif unrecognised is not None:
            print(
                f"\n[warn] #{args.issue_number}'s {unrecognised}; parent check skipped.",
                file=sys.stderr,
            )
        else:
            print("\n[cascade] no parent ref found in body; parent check skipped.")
        milestone_nums = issue_milestones(issue)
        if milestone_nums:
            print(
                f"\n[cascade] milestones to check for eligibility: "
                f"{', '.join(f'#{n}' for n in milestone_nums)}"
            )
            for mnum in milestone_nums:
                _check_milestone_eligibility(mnum, config, issue_types, classification)

    # Fire after_close_issue hooks per DEC-024. The occurrence is when the issue
    # was closed: a re-run on the same close reads the same time, so its hook
    # comment posts nothing new, and a close after a reopen has a time of its
    # own, so its comment posts (#1243). An issue already closed when this run
    # began carries the time in the read made then; one this run closed is read
    # again, and only if a `post-comment` hook is about to post.
    closed_at = str(issue.get("closedAt") or "") if state == "closed" else ""
    fire_hooks(
        "after_close_issue",
        context={
            "issue": {
                "number": args.issue_number,
                "title": str(issue.get("title", "")) if issue else "",
            },
        },
        config=config,
        capability_root=capability_root,
        occurrence=lambda: closed_at or _closed_at(args.issue_number, config),
    )

    return 0


# ---- pr-merge close through a named PR (#1049) -----------------------


def _close_leaf_through_pr(
    args: argparse.Namespace,
    *,
    structural_type: str | None,
    body: str,
    labels: list[str],
    config: dict,
    substrate_map: axis_labels.SubstrateMap | None,
    close_move: _CloseMove,
) -> int | None:
    """Close an open leaf as completed through merged PR ``args.pr``.

    The `pr-merge-into-main` closure trigger, for a leaf whose PR closed another
    issue and never named this one. Refuses a container (containers close
    through the cascade), a PR that is not merged, and — as every closure path
    does — an unticked checkbox (DEC-007). Returns the exit code to stop with,
    or None once the issue is closed, labelled and ``close_move`` recorded, so
    the caller runs the closure cascade and the after-close hooks.
    """
    issue_number = args.issue_number
    if structural_type != "task":
        kind = structural_type or "of an unrecognised type"
        print(
            f"\nerror: --pr closes a leaf (a Task) through the merged PR that "
            f"completed it; #{issue_number} is {kind}. A container closes "
            "through --mode=cascade-eligibility-close once every child has "
            "closed.",
            file=sys.stderr,
        )
        return 2

    pr = _gh_get_pr(args.pr, config)
    if pr is None:
        return 2
    if not _pr_is_merged(pr):
        pr_state = str(pr.get("state") or "not merged").lower()
        print(
            f"\n[refused] PR #{args.pr} is {pr_state}, not merged — a leaf "
            "closes as completed only through a merged PR.",
            file=sys.stderr,
        )
        return 1

    unticked = [] if args.skip_checkbox_gate else _unticked_boxes(body)
    if unticked:
        print(
            "\n"
            + _checkbox_refusal(
                unticked,
                remedy=(
                    "tick or remove each unticked checkbox before closing, "
                    "or pass --skip-checkbox-gate (discouraged)."
                ),
            ),
            file=sys.stderr,
        )
        return 1

    print(f"\ncompleted by: PR #{args.pr} (merged)")
    if args.dry_run:
        print(
            "\n[dry-run] would comment the reference, close "
            f"#{issue_number} as completed and reconcile its labels; nothing "
            "written."
        )
        return 0
    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    key, comment_body = _pr_merge_close_comment(args.pr)
    if not post_audit_once("issue", issue_number, key, comment_body, config, run=gh_run):
        return 3
    if not _gh_close_issue(issue_number, reason="completed", config=config):
        return 3
    if not reconcile_state_labels_to_done(
        issue_number,
        labels,
        config,
        gh_run=gh_run,
        substrate_map=substrate_map,
    ):
        return 3
    close_move.record(pr_merge_close_reason(args.pr, closed_by_merge=False))
    print(f"\n[ok] closed #{issue_number} (pr-merge through PR #{args.pr}, completed).")
    return None


def _pr_is_merged(pr: dict) -> bool:
    """Whether a `gh pr view` payload describes a merged PR."""
    return str(pr.get("state") or "").upper() == "MERGED" or bool(pr.get("mergedAt"))


def _pr_merge_close_comment(pr_number: int) -> tuple[str, str]:
    """The reference comment a `--pr` close posts, and its idempotency key.

    The key makes the comment retry-safe: a run that posted it and then failed
    to close finds it on the re-run and does not post it again.
    """
    key = _audit.audit_key(PR_MERGE_CLOSE_WRITER, str(pr_number))
    body = (
        f"[pr-merge close] completed by merged PR #{pr_number}.\n\n"
        "Closed via `pkit project-management close-issue --mode=pr-merge "
        f"--pr {pr_number}` "
        "(per [project-management:DEC-006-state-machine-and-cascade]).\n"
        f"{key}"
    )
    return key, body


# ---- recording the close (#1231) ------------------------------------


@dataclass(frozen=True)
class _CloseMove:
    """The lifecycle move a close makes — to done, from where the issue was —
    recorded with the process engine once the close and its label reconcile
    have landed (DEC-049: one journal entry per governed move)."""

    issue_number: int
    #: Where the issue was before the close (`state_before_close`), or None when
    #: nothing records it (a `derive`-bound state).
    from_state: str | None
    #: Why the move is not recorded although it is one: the workflow declares
    #: no `from_state → done` for the issue's type. Empty when it does.
    undeclared: str
    actor: str | None

    @classmethod
    def read(
        cls,
        issue_number: int,
        issue: dict,
        labels: list[str],
        structural_type: str | None,
        *,
        workflow: dict,
        substrate_map: axis_labels.SubstrateMap | None,
        actor: str | None,
    ) -> _CloseMove:
        """The move closing ``issue`` makes, read from the issue as fetched —
        before this run writes anything."""
        from_state = infer.state_before_close(
            milestone=issue.get("milestone"), labels=labels, substrate_map=substrate_map
        )
        undeclared = ""
        if from_state is not None and from_state != DONE_STATE:
            # The engine does not read a transition's `applies_to` (a pm field),
            # so the type half of "is this move declared" is asked here, of the
            # table move-issue refuses on.
            if DONE_STATE not in infer.legal_targets(workflow, from_state, structural_type or ""):
                kind = repr(structural_type) if structural_type else "an unrecognised type"
                undeclared = (
                    f"no transition {from_state!r} → {DONE_STATE!r} declared in "
                    f"workflow.yaml for {kind}"
                )
        return cls(issue_number, from_state, undeclared, actor)

    def record(self, reason: str) -> None:
        """Hand the move to the engine with ``reason`` — the close mode — on its
        entry, through the path ``move-issue`` records its moves through.

        One engine call, and none when there is nothing to record: the issue
        was at done already (its label said so; whoever wrote it recorded the
        move, so a re-run adds nothing), or nothing says where it was. A move
        the workflow does not declare for the issue's type is not handed over
        and is warned about as a refused one is; a move the engine refuses is
        warned about by the shared path. Neither fails the close.
        """
        if self.from_state is None or self.from_state == DONE_STATE:
            return
        if self.undeclared:
            report_unrecorded(self.issue_number, f"this move was not recorded: {self.undeclared}")
            return
        journal_move(self.issue_number, self.from_state, DONE_STATE, self.actor, reason=reason)


# ---- parent eligibility ---------------------------------------------


def _check_parent_eligibility(parent_num: int, config: dict) -> None:
    """Report whether a parent is eligible to close.

    Eligibility per DEC-006: every open child has closed, AND parent's
    own checkboxes are ticked. We surface the report; we do not auto-
    close (DEC-006 explicit: closure is never auto).
    """
    parent = _gh_get_issue(parent_num, config)
    if parent is None:
        print(f"  [warn] could not fetch parent #{parent_num}", file=sys.stderr)
        return
    state = str(parent.get("state", "")).lower()
    if state == "closed":
        print(f"  · parent #{parent_num} already closed")
        return
    body = str(parent.get("body") or "")
    unticked = _unticked_boxes(body)
    if unticked:
        print(f"  · parent #{parent_num} open; not eligible ({len(unticked)} unticked box(es))")
        return
    print(
        f"  · parent #{parent_num} open; checkboxes complete — "
        "eligible to close pending sibling check"
    )


def _check_milestone_eligibility(
    number: int, config: dict, issue_types: dict, classification: dict
) -> None:
    """Report whether a Milestone the closed issue sits in became closeable.

    The Milestone counterpart of :func:`_check_parent_eligibility` (#414). A
    content-based or `either` Milestone is eligible once every child issue is
    closed — the condition `close-milestone` closes it on, read through the
    same `_lib.milestone` reads, so the report and the close cannot disagree.
    A date-based Milestone closes on its date, so its children closing makes
    nothing eligible. We surface the report with the command that closes the
    Milestone; we do not close it (DEC-016: closing it is the user's gesture).
    """
    milestone = fetch_milestone(number, config)
    if milestone is None:
        print(f"  [warn] could not fetch milestone #{number}", file=sys.stderr)
        return
    if str(milestone.get("state", "")).lower() == "closed":
        print(f"  · milestone #{number} already closed")
        return
    trigger, inferred = resolve_close_trigger(
        str(milestone.get("description") or ""), milestone.get("due_on")
    )
    trigger_text = f"{trigger} (inferred)" if inferred else trigger
    if trigger not in CONTENT_TRIGGERS:
        print(
            f"  · milestone #{number} open; {trigger_text} — it closes on its "
            "date, not when its children close"
        )
        return
    children = list_milestone_children(
        number, str(milestone.get("title", "")), config, issue_types, classification
    )
    if children is None:
        print(f"  [warn] could not list milestone #{number}'s children", file=sys.stderr)
        return
    open_count = sum(1 for child in children if child["state"] != "closed")
    if open_count:
        print(f"  · milestone #{number} open; not eligible ({open_count} open child issue(s))")
        return
    print(
        f"  · milestone #{number} open; {trigger_text}, all {len(children)} "
        f"child issue(s) closed — eligible to close: run "
        f"`pkit pm close-milestone {number}`"
    )


# ---- process-engine cascade delegation (DEC-034 / DEC-033 D5) -------
#
# The CHILDREN-HALF of close-eligibility is the shared process engine's
# cascade fold (`pkit process cascade`, COR-037), invoked by subprocess
# (never imported, ADR-020). The fold reads workflow.yaml's
# `process.cascade` (all-over-`done` over the parent's child issues). The
# wrapper keeps the OTHER half — the DEC-007 checkbox gate — local, and
# ANDs the two. close-issue does not recompute the fold itself. The process
# address is `_lib.move_journal`'s, the one the close's journal entry uses.


def _engine_cascade_fold(parent_num: int) -> dict | None:
    """Read the parent's children-half cascade fold from the engine.

    Returns the fold dict `{opened, indeterminate, reached, total, reason, ...}`
    (the `process cascade --json` payload's `cascade` object), or None when the
    engine cannot be reached at all (a missing `pkit`, a crash) — the caller maps
    None to a fail-closed HOLD (never an auto-open). A reachable engine that
    cannot resolve the fold reports `indeterminate: true` (also a HOLD); a
    determinate fold reports `opened` true/false.
    """
    argv = [
        "pkit",
        "process",
        "cascade",
        PROCESS_ADDRESS,
        "--subject",
        str(parent_num),
        "--json",
    ]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    except (OSError, FileNotFoundError):
        return None
    # The command exits non-zero when the fold is NOT open (by design); the JSON
    # on stdout is authoritative regardless of exit code, so parse it either way.
    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    cascade = payload.get("cascade")
    return cascade if isinstance(cascade, dict) else None


def _find_open_children(parent_num: int, config: dict) -> list[int] | None:
    """Return the OPEN children of a container — diagnostic colour for the
    refused-cascade message only (the ENGINE fold is the decision).

    Children are resolved through the SAME containment read-seam
    (``_lib.containment.resolve_children``) the engine's ``cascade_members``
    predicate and ``show-tree`` use — native sub-issues where present, textual
    child-side parent-refs otherwise, native-wins (DEC-005). Routing this through
    the one seam is the ADR-026 point: no consumer re-derives containment by
    re-parsing body parent-refs. The seam returns ALL children; this helper
    filters to the still-OPEN ones for the "what to close first" hint.

    Diagnostic only: the engine fold is the decision, and the sole caller reaches
    this after that fold has already refused. Empty list = all children closed
    (or none). None means "cannot say" — a gh failure, or a resolution the seam
    could not vouch for — and the hint is omitted rather than shown short.
    """
    # Acquisition belongs to the seam (ADR-035 §5). This used to fetch 500 rows
    # and compute open children with NO truncation check, so past 500 issues the
    # hint could omit still-open children — or list none at all — while the user
    # read it as the full set of what to close. It never closed anything: the
    # engine fold is the decision and it had already refused (see the call site).
    # A short list presented as a whole one is still worth refusing over (#846).
    corpus = containment.fetch_issue_corpus(config, fields="number,state,body")
    if corpus is None:
        print("error: gh issue list failed.", file=sys.stderr)
        return None
    states = corpus.states
    resolution = containment.resolve_children(
        config,
        parent_number=parent_num,
        corpus=corpus.bodies,
        corpus_complete=corpus.complete,
    )
    if not resolution.complete:
        print(
            f"error: cannot determine #{parent_num}'s open children — "
            f"{resolution.incomplete_reason}. Refusing rather than closing over "
            "a child that may exist.",
            file=sys.stderr,
        )
        return None
    open_children = [n for n in resolution.numbers if states.get(n) != "closed"]
    return sorted(open_children)


# ---- gh wrappers ----------------------------------------------------


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(issue_number, config, fields="title,body,state,labels,milestone,closedAt")


def _closed_at(issue_number: int, config: dict) -> str:
    """When the issue was last closed, as GitHub reports it, or "" when it is
    open or cannot be read."""
    issue = gh_get_issue(issue_number, config, fields="closedAt")
    return str((issue or {}).get("closedAt") or "")


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


def _gh_get_pr(pr_number: int, config: dict) -> dict | None:
    return gh_get_pr(pr_number, config, fields="number,state,mergedAt,url")


def _gh_close_issue(issue_number: int, *, reason: str = "completed", config: dict) -> bool:
    cmd = ["gh", "issue", "close", str(issue_number)]
    if reason:
        cmd.extend(["--reason", reason])
    try:
        # Through the gh seam, so the adopter's configured host applies (DEC-023).
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue close failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


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
