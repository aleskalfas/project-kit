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
    `Closes #N` keyword. The script reconciles the labels of the issue GitHub
    closed and runs the cascade pass on parents after the fact; it does not
    itself close the issue, and refuses an open one (#1968).
    With `--pr <M>` it DOES close an open leaf (a Task) whose work landed in
    merged PR M where GitHub did not close it (#1049): PR M is verified
    merged and related to the issue — its body closes the issue, or it was
    merged from the issue's branch, `<type>/<N>-<slug>` (DEC-013) — and the
    relation found is named (#1968). The DEC-007 checkbox close-gate runs, the
    reference is posted as a comment, and the issue closes as completed before
    the cascade pass. A merged PR that does not relate to the issue is refused.
  * `--mode=cascade-eligibility-close` — closes a container (epic/feature/
    umbrella) once every child is closed AND its own checkboxes are ticked
    (the DEC-007 gate is non-skippable here). Implements the
    `cascade-eligibility-close` trigger this script previously only reported.
    Closes via `gh issue close --reason completed`.

A won't-do close, a container's close and a leaf's close through ``--pr`` are
moves the person authorises, a hard reject when that is missing (DEC-006), as
``move-issue`` holds such a move: ``--yes`` authorises the close, a terminal
asks, and with neither the close is refused before anything is written (#1936,
#1968). A dry run writes nothing and asks for no authorisation.

All three paths reconcile the issue's ``state:*`` labels after closing: any
non-terminal label (``state:todo``, ``state:backlog``, ``state:in-progress``,
``state:review``) is removed and ``state:done`` is ensured.  The reconcile
logic is shared with ``move-issue`` via ``_lib.labels.reconcile_state_labels_to_done``
so there is no duplicated label-mutation code.

After closing, every path runs the closure cascade (DEC-006), which reports and
never closes: each parent issue in this repository the close gate counts the
issue under — its native parent and the parent its first line names, as the
containment seam resolves them (``containment.resolve_parent``) — is checked for
close eligibility. A parent is reported eligible only once it has no open child
left, by the process engine's fold over its children (``pkit process cascade``,
the reading ``--mode=cascade-eligibility-close`` takes), and its own checkboxes
are ticked, with the command that closes it; a parent with an open child is
reported with that child named (#1937). Each Milestone the issue sits in (its
native Milestone field, or a ``Milestone: [#<n>](../milestone/<n>)`` body ref)
is checked too. A
content-based (or ``either``) Milestone whose every child issue is closed is
reported as eligible, with the ``close-milestone`` command that closes it
(#414); a date-based one closes on its date, so its children closing makes
nothing eligible.

Each close is a governed move to done, recorded with the process engine through
the path ``move-issue`` records its moves through (``_lib.move_journal``,
``pkit process move --from``; #1231): after the close and its label reconcile,
one move from the state the issue held before the close, with the close mode
as the entry's reason. That state is read from the issue as fetched at the
start, before anything is written (``lifecycle_inference.state_before_close``,
the reading the forward cascade takes too): its state label, else its
milestone (Backlog, inferred), else — for an issue still open — Todo, read as if
it were open, so an issue GitHub closed when a pull request merged reads where
the merge found it. An issue GitHub closed with neither a state label nor a
milestone carries nothing of where it was, and its close is not recorded from a
guessed Todo. An issue whose label already says done was moved there by whoever wrote
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
     `--pr` names a PR that is not merged or does not relate to the issue /
     pr-merge mode without `--pr` on an open issue
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
    bootstrap_gate,
    containment,
    engine_said,
    issue_branch,
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
from _lib.pr_validation import extract_closing_issues
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
            "`pr-merge` is the cascade-only hook after GitHub-native close, "
            "refusing an open issue (with --pr, it closes an open leaf itself); "
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
            "pr-merge mode only: the merged PR that completed this issue where "
            "GitHub did not close it. An OPEN leaf (a Task) is closed as "
            "completed only where PR M is merged and relates to it — its body "
            "closes the issue, or it was merged from the issue's branch "
            "(`<type>/<N>-<slug>`); the relation found is named, the DEC-007 "
            "checkbox close-gate runs, the reference is posted as a comment, "
            "then the closure cascade runs. Without --pr, pr-merge mode only "
            "reconciles labels after GitHub's own close, and refuses an open "
            "issue."
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
        help=(
            "Skip the confirmation prompt. A won't-do close, a container's "
            "close and a leaf's close through --pr are the person's to "
            "authorise (DEC-006): with no terminal to ask at, they are refused "
            "without --yes."
        ),
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
        held = _authorise(
            args.yes,
            close=f"closing #{args.issue_number} as won't do",
            prompt="Proceed? [y/N] ",
        )
        if held is not None:
            return held

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
        if state != "closed":
            # No merged PR is named, so nothing says this issue's work landed:
            # a move to Done is the merge's that completed it, or a person's
            # won't-do (DEC-006). Refused before anything is written (#1968).
            print(
                f"\n[refused] #{args.issue_number} is open, and pr-merge mode without "
                "--pr moves no open issue to Done: it reconciles the labels of an "
                "issue GitHub closed as a PR merged.\n"
                "          → If a merged PR completed it, re-run with --pr <M>, naming "
                "that PR.\n"
                "          → Otherwise close it as won't do, which asks the person: "
                f'close-issue {args.issue_number} --reason "<R>".',
                file=sys.stderr,
            )
            return 1
        if args.pr is not None:
            print(
                f"\n[noop] #{args.issue_number} is already closed; --pr is not "
                "needed — reconciling labels only."
            )
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
        #   opened == False  -> held; refuse. The engine marks the fold
        #                       indeterminate for an open child as well as for a
        #                       read it could not make (COR-037: an unresolved
        #                       member holds the fold unresolved), so the refusal
        #                       reads the children itself and says what it found
        #                       (`_refuse_held`): open children, named with what
        #                       releases the container; children that could not
        #                       be read, named with their remedy; both, each with
        #                       its own.
        #   fold is None     -> `pkit` itself was unreachable (could not even invoke
        #                       the engine); HOLD fail-closed -> refuse.
        # The two differ in exit code (1 = engine reachable but held; 3 = engine
        # unreachable), so callers/CI can tell a policy refusal from an environment
        # failure. Keep the 3-vs-1 split: it is a deliberate two-failure-surface
        # contract, not noise.
        fold = _engine_cascade_fold(args.issue_number)
        if fold is None:
            _say_read_failed(args.issue_number, None, _OpenChildren())
            return 3
        if not fold.get("opened"):
            return _refuse_held(args.issue_number, fold, config)

        if args.dry_run:
            print(
                "\n[dry-run] eligible (all children closed, checkboxes ticked); "
                "gh would close with --reason completed."
            )
            return 0
        held = _authorise(
            args.yes,
            close=f"closing container #{args.issue_number}",
            prompt="Close cascade-eligible container? [y/N] ",
        )
        if held is not None:
            return held

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
        _report_parents(args.issue_number, body, structural_type, issue_types, config)
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


# ---- the person's authorisation (#1936) ------------------------------


def _authorise(yes: bool, *, close: str, prompt: str) -> int | None:
    """Ask for the person's authorisation of a close DEC-006 holds for them.

    A won't-do close (Backlog/Todo → Done), a container's close (In Progress
    → Done) and a leaf's close through the merged PR ``--pr`` names (#1968)
    are user-authorised, a hard reject when the authorisation is missing — as
    ``move-issue`` holds such a move. ``--yes`` gives it; at a terminal the
    person is asked. With neither, the close is refused before anything is
    written. Returns None once authorised, else the exit code to stop with: 1
    for the refusal, 0 where the person declined at the prompt.
    """
    if yes:
        return None
    if not sys.stdin.isatty():
        print(
            f"[refused] {close} is user-authorised (hard-reject on violation).\n"
            "          → Pass --yes to confirm the authorisation, "
            "or re-run from an interactive shell.",
            file=sys.stderr,
        )
        return 1
    reply = input(prompt).strip().lower()
    if reply not in ("y", "yes"):
        print("aborted.", file=sys.stderr)
        return 0
    return None


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

    The `pr-merge-into-main` closure trigger, for a leaf GitHub did not close
    as the PR merged — a base it does not close issues on, or a PR from the
    leaf's branch whose body does not name it. Refuses a container (containers
    close through the cascade), a PR that is not merged, a merged PR that does
    not relate to the leaf (:func:`_relation`, #1968), and — as every closure
    path does — an unticked checkbox (DEC-007). Returns the exit code to stop
    with, or None once the issue is closed, labelled and ``close_move``
    recorded, so the caller runs the closure cascade and the after-close hooks.
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
    relation = _relation(pr, issue_number)
    if relation is None:
        head = str(pr.get("headRefName") or "")
        branch = f"its branch `{head}`" if head else "its branch"
        print(
            f"\n[refused] PR #{args.pr} has merged, but nothing in it relates it to "
            f"#{issue_number}: its body does not close #{issue_number}, and {branch} is "
            f"not #{issue_number}'s (`<type>/{issue_number}-<slug>`). A leaf closes as "
            "completed only through the merged PR that completed it.\n"
            f"          → If PR #{args.pr} did, name #{issue_number} in it "
            f"(`edit-pr {args.pr} --closes {issue_number}`), then run this again.\n"
            "          → Otherwise close it as won't do, which asks the person: "
            f'close-issue {issue_number} --reason "<R>".',
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

    print(f"\ncompleted by: PR #{args.pr} (merged), {relation}")
    if args.dry_run:
        print(
            "\n[dry-run] would comment the reference, close "
            f"#{issue_number} as completed and reconcile its labels; nothing "
            "written."
        )
        return 0
    held = _authorise(
        args.yes,
        close=f"closing #{issue_number} as completed through PR #{args.pr}",
        prompt="Proceed? [y/N] ",
    )
    if held is not None:
        return held

    key, comment_body = _pr_merge_close_comment(args.pr, relation)
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


def _relation(pr: dict, issue_number: int) -> str | None:
    """What relates merged PR ``pr`` to the issue, in words, or None (#1968).

    A PR relates to an issue where its body closes it — the closing references
    as `open-pr`, `validate-pr` and `done-work` read them — or where it was
    merged from the issue's branch, `<type>/<N>-<slug>` (DEC-013), the shape the
    verbs find an issue's branch by. Both found, both are named. A merged PR
    with neither records nothing of having completed the issue, so it is no
    evidence for closing it as completed.
    """
    found: list[str] = []
    if issue_number in extract_closing_issues(str(pr.get("body") or "")):
        found.append(f"whose body closes #{issue_number}")
    head = str(pr.get("headRefName") or "")
    if issue_branch.is_issue_branch(head, issue_number):
        found.append(f"whose branch `{head}` is #{issue_number}'s")
    return " and ".join(found) or None


def _pr_merge_close_comment(pr_number: int, relation: str) -> tuple[str, str]:
    """The reference comment a `--pr` close posts, naming the relation found,
    and its idempotency key.

    The key makes the comment retry-safe: a run that posted it and then failed
    to close finds it on the re-run and does not post it again.
    """
    key = _audit.audit_key(PR_MERGE_CLOSE_WRITER, str(pr_number))
    body = (
        f"[pr-merge close] completed by merged PR #{pr_number}, {relation}.\n\n"
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
    #: nothing records it (a `derive`-bound state, or an issue already closed
    #: with neither a state label nor a milestone).
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
            milestone=issue.get("milestone"),
            labels=labels,
            closed=str(issue.get("state", "")).lower() == "closed",
            substrate_map=substrate_map,
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

# What the closure cascade does not do with a native parent in another
# repository, as the containment seam's remedy line says it (`remedy(abroad=…)`).
_NO_CHECK_ABROAD = "the closure cascade does not check"


def _report_parents(
    issue_number: int, body: str, structural_type: str | None, issue_types: dict, config: dict
) -> None:
    """The closure cascade over the closed issue's parent issues.

    The parent is resolved by the containment seam from one read of the
    issue's record (`containment.resolve_parent`), and every parent in this
    repository the close gate counts the issue under — its native parent and the
    issue its first line names, one or both — is checked for eligibility, so the
    report and the gate cannot disagree. How the two records stand is said after
    the checks, in the seam's words: a first line in a form the issue's type does
    not allow (the parent it names is checked all the same), a native parent
    with no first line naming it, two that disagree, a native parent in another
    repository (which is not checked), or a record that could not be read (the
    first line's parent is checked, and the native one was not compared). An
    issue with neither record names no parent to check, and a first line naming
    the issue itself names none: that is said, and nothing is checked from it.
    """
    resolution = containment.resolve_parent(
        config,
        issue_number=issue_number,
        structural_type=structural_type,
        issue_types=issue_types,
        body=body,
    )
    parents = resolution.local_parents
    if parents:
        print(
            f"\n[cascade] parents to check for eligibility: {', '.join(f'#{n}' for n in parents)}"
        )
        for parent in parents:
            _check_parent_eligibility(parent, config)
    if resolution.self_note is not None:
        print(
            f"\n[warn] {resolution.self_note}; the closure cascade checks no parent from it.",
            file=sys.stderr,
        )
    kind = resolution.kind
    if kind is containment.ParentKind.NONE:
        print(
            "\n[cascade] no parent issue: neither a native parent nor one named on the first "
            "line; parent check skipped."
        )
        return
    if resolution.form_note is not None:
        print(
            f"\n[warn] {resolution.form_note}; #{resolution.named} is checked as its parent "
            "all the same.",
            file=sys.stderr,
        )
    if kind is containment.ParentKind.UNREAD:
        consequence = (
            f"#{resolution.named} is checked, and the native parent was not compared"
            if resolution.named is not None
            else "parent check skipped"
        )
        print(f"\n[warn] {resolution.fact}; {consequence}.", file=sys.stderr)
        return
    if resolution.fact is None:
        return
    native = resolution.native
    if kind is containment.ParentKind.NATIVE_ONLY and native is not None and not native.repository:
        print(f"\n[note] {resolution.fact}.")
        print(f"  {resolution.remedy(abroad=_NO_CHECK_ABROAD)}")
        return
    print(f"\n[warn] {resolution.fact}.", file=sys.stderr)
    print(f"  {resolution.remedy(abroad=_NO_CHECK_ABROAD)}", file=sys.stderr)


def _check_parent_eligibility(parent_num: int, config: dict) -> None:
    """Report whether a parent has an open child left, and whether it is
    eligible to close.

    Eligibility per DEC-006 is the conjunction DEC-034 names: the parent has no
    open child left, AND its own checkboxes are ticked. Whether a child is open
    is the process engine's fold over the parent's children, read as
    ``--mode=cascade-eligibility-close`` reads it (:func:`_engine_cascade_fold`,
    #1937), so a parent is reported eligible only where that close would close
    it, with the command that asks the person to authorise the close. A fold
    that did not open is said with what holds it (:func:`_report_held_parent`).
    We surface the report; we do not auto-close (DEC-006 explicit: closure is
    never auto).
    """
    parent = _gh_get_issue(parent_num, config)
    if parent is None:
        print(f"  [warn] could not fetch parent #{parent_num}", file=sys.stderr)
        return
    state = str(parent.get("state", "")).lower()
    if state == "closed":
        print(f"  · parent #{parent_num} already closed")
        return
    fold = _engine_cascade_fold(parent_num)
    if fold is None or not fold.get("opened"):
        _report_held_parent(parent_num, fold, config)
        return
    unticked = _unticked_boxes(str(parent.get("body") or ""))
    if unticked:
        print(
            f"  · parent #{parent_num} open; no open child left, but not eligible "
            f"({len(unticked)} unticked box(es))"
        )
        return
    print(
        f"  · parent #{parent_num} open; no open child left and checkboxes complete — "
        f"eligible to close: run `pkit pm close-issue {parent_num} "
        "--mode=cascade-eligibility-close`"
    )


def _report_held_parent(parent_num: int, fold: dict | None, config: dict) -> None:
    """Say why a parent the engine's fold did not open is not eligible.

    Its open children are named, from the containment seam's reading of them
    (:func:`_find_open_children`), as the refusal of a held container names
    them. Where the engine could not be run, its fold stopped on a read before
    it counted a member (:func:`_stopped_on_a_read`), or no open child is
    found, whether one is open is not known: the engine's reason is said, with
    what a predicate it could not evaluate said.
    """
    if fold is None:
        print(
            f"  · parent #{parent_num} open; not eligible — the process engine could not "
            "fold its children, so whether one is open is not known"
        )
        return
    if not _stopped_on_a_read(fold):
        children = _find_open_children(parent_num, config)
        if children.open:
            named = ", ".join(_child_named(child) for child in children.open)
            print(f"  · parent #{parent_num} open; not eligible — open child(ren): {named}")
            return
    print(
        f"  · parent #{parent_num} open; not eligible — whether a child is open is not "
        f"known: {fold.get('reason') or 'the fold did not open.'}"
    )
    for line in engine_said.said_lines(fold.get("stderr_tail"), "      "):
        print(line)


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


@dataclass(frozen=True)
class _OpenChildren:
    """A container's children as the refusal reads them: the open ones, the
    ones whose state could not be read (each with why), and why the child set
    itself could not be read in full, when it could not."""

    open: tuple[containment.ResolvedChild, ...] = ()
    unread: tuple[tuple[containment.ResolvedChild, str], ...] = ()
    incomplete: str | None = None


def _refuse_held(parent_num: int, fold: dict, config: dict) -> int:
    """Say what holds a container the engine's fold did not open; exit code 1.

    The fold is the decision; this says what held it, from what the containment
    seam's reading of the children finds (:func:`_find_open_children`) — not
    from the engine's reason, which names whichever member the fold stopped at,
    so it cannot tell an open child from a read that failed when both are there.
    Open children are the "held by open children" block, each with what
    releases the container (:func:`_say_held_open`). Children that could not be
    read, or a child set that could not be read in full, are the "a read failed"
    block, each with its remedy (:func:`_say_read_failed`) — and so is a fold
    the engine says stopped on a read before it counted a member that holds it
    (:func:`_stopped_on_a_read`), a failure no read here can see. Both found,
    both blocks are said; the engine's reason goes in the second only where it
    names the read that failed, not where it may name an open child. Neither
    found, the engine's reason is said under a header that claims no cause
    (:func:`_say_held_unexplained`).
    """
    children = _find_open_children(parent_num, config)
    stopped_on_a_read = _stopped_on_a_read(fold)
    failed = bool(children.unread or children.incomplete) or stopped_on_a_read
    if children.open:
        _say_held_open(parent_num, children)
    if failed:
        _say_read_failed(
            parent_num, fold, children, engine_reason=stopped_on_a_read or not children.open
        )
    if not children.open and not failed:
        _say_held_unexplained(parent_num, fold)
    return 1


def _stopped_on_a_read(fold: dict) -> bool:
    """Whether the engine's fold stopped on a read before it counted a member
    that holds it — unresolved, with every member it counted done (``reached``
    equal to ``total``): its members list, or a candidate's membership, could
    not be read. The engine counts a member only once its membership is read, so
    the one it stopped at is never an open child here."""
    reached, total = fold.get("reached"), fold.get("total")
    return (
        fold.get("indeterminate") is True
        and isinstance(reached, int)
        and isinstance(total, int)
        and reached == total
    )


def _say_held_open(parent_num: int, children: _OpenChildren) -> None:
    """The refusal for a container held by open children: each named, a child in
    another repository with its repository, and what releases the container."""
    print(
        f"\n[refused] not cascade-eligible — #{parent_num} is held by its open child(ren):",
        file=sys.stderr,
    )
    for child in children.open:
        print(f"  - {_child_named(child)}", file=sys.stderr)
    print(
        f"  → close each open child; #{parent_num} becomes eligible when the last one closes.",
        file=sys.stderr,
    )
    for child in children.open:
        if child.repository is not None:
            first, *rest = _released_abroad(parent_num, child)
            print(f"  → {first}", file=sys.stderr)
            for line in rest:
                print(f"    {line}", file=sys.stderr)


def _say_read_failed(
    parent_num: int, fold: dict | None, children: _OpenChildren, *, engine_reason: bool = True
) -> None:
    """The refusal for a container held because a read failed: the engine's
    reason (unless ``engine_reason`` is false, where open children were found
    and the reason may name one of them), what the predicate the fold could not
    evaluate said, and each read of the children that failed. A child in
    another repository that could not be read is given its two ways out — made
    readable, or its link removed from here — since a run repeated under the
    same access fails the same way; the re-run advice goes with every other
    failed read. ``fold`` is ``None`` where the engine could not be run at all."""
    print(
        "\n[refused] could not resolve the children-half of cascade "
        "eligibility (held fail-closed):",
        file=sys.stderr,
    )
    if fold is None:
        print("  → the process engine could not fold the children.", file=sys.stderr)
    elif engine_reason:
        print(f"  → {fold.get('reason') or 'the fold did not open.'}", file=sys.stderr)
    # What a predicate the fold could not evaluate said, as the engine
    # reports it (`stderr_tail`).
    said = fold.get("stderr_tail") if fold is not None else None
    for line in engine_said.said_lines(said, "    "):
        print(line, file=sys.stderr)
    if children.incomplete:
        print(
            f"  → #{parent_num}'s children could not be read in full: {children.incomplete}",
            file=sys.stderr,
        )
    for child, why in children.unread:
        if child.repository is None:
            print(f"  → {child.ref} could not be read: {why}", file=sys.stderr)
            continue
        print(f"  → {_child_named(child)}, could not be read: {why}", file=sys.stderr)
        for line in _unread_abroad(parent_num, child):
            print(f"    {line}", file=sys.stderr)
    abroad_only = bool(children.unread) and all(
        child.repository is not None for child, _ in children.unread
    )
    if fold is None or children.incomplete or not abroad_only or _stopped_on_a_read(fold):
        print(
            "  → re-run once `gh` is reachable and every child's state is "
            "readable; the container holds until the fold resolves.",
            file=sys.stderr,
        )


def _say_held_unexplained(parent_num: int, fold: dict) -> None:
    """The refusal where the engine's fold did not open and the children read
    here show neither an open child nor a read that failed: the engine's reason
    and what a predicate said, under a header that claims no cause."""
    print(
        f"\n[refused] not cascade-eligible — the process engine's fold over #{parent_num}'s "
        "children did not open:",
        file=sys.stderr,
    )
    print(f"  → {fold.get('reason') or 'the engine gave no reason.'}", file=sys.stderr)
    for line in engine_said.said_lines(fold.get("stderr_tail"), "    "):
        print(line, file=sys.stderr)
    print(
        f"  → the children read here are closed and readable; #{parent_num} holds until "
        "the fold opens.",
        file=sys.stderr,
    )


def _child_named(child: containment.ResolvedChild) -> str:
    """``#11``, or ``owner/repo#42, a sub-issue in another repository``."""
    if child.repository is None:
        return child.ref
    return f"{child.ref}, a sub-issue in another repository"


def _unlink_command(parent_num: int, child: containment.ResolvedChild) -> str:
    """The command that removes a child's sub-issue link from the parent, run in
    this repository — printed, never run (`containment.remove_sub_issue_command`)."""
    return containment.remove_sub_issue_command(
        parent_number=parent_num, child_database_id=child.database_id
    )


def _released_abroad(parent_num: int, child: containment.ResolvedChild) -> list[str]:
    """What releases a container from an open child in another repository, where
    pm writes nothing: the child closing there, or its link removed from this
    repository, by the command on the second line."""
    return [
        f"{child.ref} holds #{parent_num} until it is closed in {child.repository}, or "
        f"its sub-issue link under #{parent_num} is removed, in this repository, with:",
        f"  {_unlink_command(parent_num, child)}",
    ]


def _unread_abroad(parent_num: int, child: containment.ResolvedChild) -> list[str]:
    """The two ways out for a child in another repository that could not be
    read: made readable, or its link removed from this repository."""
    return [
        f"two ways out: make {child.ref} readable to the account `gh` uses here, then "
        f"run this again; or remove its sub-issue link under #{parent_num}, in this "
        "repository, with:",
        f"  {_unlink_command(parent_num, child)}",
    ]


def _find_open_children(parent_num: int, config: dict) -> _OpenChildren:
    """Read which of a container's children are OPEN — what the refusal of a
    held container names (the ENGINE fold is the decision).

    Children are resolved through the SAME containment read-seam
    (``_lib.containment.resolve_children``) the engine's ``cascade_members``
    predicate and ``show-tree`` use — native sub-issues together with child-side
    first-line parent-refs, native-wins on a child present both ways (DEC-005).
    Routing this through the one seam is the ADR-035 point: no consumer
    re-derives containment by re-parsing body parent-refs. A child in this
    repository is read from the issue list; a native sub-issue in another
    repository from its own record there — one read, by its open/closed alone,
    as the fold reads it, and never taken for this repository's issue of the
    same number.

    A child set the seam could not vouch for is ``incomplete`` and no child is
    named from it — a short list is not served as the whole one (#846); a child
    whose state could not be read is ``unread``, with why.
    """
    # Acquisition belongs to the seam (ADR-035 §5). This used to fetch 500 rows
    # with NO truncation check, so past 500 issues the list could omit
    # still-open children while the user read it as the full set (#846).
    corpus = containment.fetch_issue_corpus(config, fields="number,state,body")
    if corpus is None:
        return _OpenChildren(incomplete="the issue list could not be read (gh failure)")
    resolution = containment.resolve_children(
        config,
        parent_number=parent_num,
        corpus=corpus.bodies,
        corpus_complete=corpus.complete,
    )
    if not resolution.complete:
        return _OpenChildren(incomplete=resolution.incomplete_reason)
    states = corpus.states
    open_children: list[containment.ResolvedChild] = []
    unread: list[tuple[containment.ResolvedChild, str]] = []
    for child in resolution.children:
        if child.repository is None:
            state = states.get(child.number)
            if state is None:
                unread.append((child, "it is not among the issues the issue list returned"))
            elif state != "closed":
                open_children.append(child)
            continue
        record = containment.read_issue_record(
            config, issue_number=child.number, repository=child.repository
        )
        if isinstance(record, containment.UnreadIssue):
            unread.append((child, record.detail))
        elif record.issue.get("state") != "CLOSED":
            open_children.append(child)
    return _OpenChildren(open=tuple(open_children), unread=tuple(unread))


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
    return gh_get_pr(pr_number, config, fields="number,state,mergedAt,url,headRefName,body")


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
