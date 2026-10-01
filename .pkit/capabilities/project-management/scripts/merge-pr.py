#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — merge-pr (verb-subject per DEC-020).

Merges a GitHub PR per the methodology's merge convention
(git-conventions.yaml's `merge` entry): one squash commit whose subject is
the PR title, no merge commits, head branch deleted on merge. Before the
merge:

  * Membership gate (DEC-021).
  * The merge queue (#1011, `_lib.merge_queue`), read before any gate so a
    run it would refuse stops before it posts anything: where the PR's base
    merges through a queue, the queue is the only path to it, so `--admin`
    and `--bypass-ci` are refused, and so are a queue that does not squash, a
    repository whose squash-commit defaults are not the PR title and body,
    and a head the queue already dropped (`--force` enqueues it again).
  * Checkbox close-gate (DEC-007) on every issue the PR closes —
    every `- [ ]` in any closing issue body must be ticked, else
    refuse. The PR body's own checkboxes also count.
  * PR title must match `titles.yaml`'s `pr` regex (Conventional
    Commits).
  * CI-status gate (#498): the PR's `statusCheckRollup` must be green.
    A failing or still-pending check refuses the merge, naming the
    offending checks, unless `--bypass-ci "<reason>"` is supplied — a
    bypassable-with-audit escape (validation-severity.yaml) dedicated to
    the CI gate that posts the audit-comment template to the PR before
    merging. The CI override is deliberately its own flag, separate from
    any general `--bypass`, so overriding another gate never silently
    clears a red CI.

Side-effects, in order (the merge mechanic lives once in `_lib.pr_merge`,
shared with `done-work`; #882):
  - The CI-bypass audit comment on the PR, BEFORE the merge, if `--bypass-ci`
    overrode a non-green CI gate. It names the short PR head and closes with a
    hidden `<!-- pkit-audit-key: merge-pr-ci-bypass:<digest> -->` hashed from
    the reason and the PR head commit, and a re-run skips only when a comment
    with exactly that body was posted, unedited, by the account `gh` posts as
    (`_lib.comment.post_audit_once`, #902) — a retry posts nothing new, a
    different reason or new commits post their own record, and nobody else's
    comment can suppress it. A failed post aborts before the merge (exit 3).
  - `gh pr merge --squash --subject <PR title> --match-head-commit <head>` —
    pinned to the head the gates read, and WITHOUT `--delete-branch`: that
    flag makes gh check out the default branch locally and delete the local
    head, and the whole command exits non-zero when the working tree cannot
    do so (a detached HEAD; the head branch checked out in a worktree, #587)
    — after the remote merge has already landed.
  - Where the base merges through a queue, the queue makes the merge
    instead: `gh pr merge <N> --auto --match-head-commit <head>` enqueues the
    PR, and merge-pr prints its place and waits for the merge — as long as
    the queue estimates plus a margin, at most 30 minutes, or
    `--wait-minutes`. When the wait ends first, or `--no-wait` returns at
    once, the run exits 4; so does a direct merge gh accepted when GitHub
    cannot then be read to confirm it merged, and a merge or an enqueue that
    got no answer back when GitHub cannot then be read to tell what it came
    to — never taken for a failed one. A push after the enqueue takes
    the PR out of the queue (exit 3). The merge mechanic, queue included, is
    `_lib.pr_merge.land`, the one `done-work` runs.
  - `after_merge_pr` hooks (DEC-024) IMMEDIATELY after the merge — once
    GitHub reports the PR merged, never on an enqueue — so no best-effort
    step stands between the irreversible merge and them. That they fired is
    then recorded in the clone (below).
  - Best-effort branch cleanup: delete the remote head ref through the API,
    then `git checkout <default_branch>`, `git pull --ff-only`, `git branch
    -D <head>`, the local delete only when everything on the branch merged.
    Each step warns with its reason and continues; none can fail the run — a
    head branch checked out in a worktree simply leaves a warning where the
    local delete would have been.

A merged PR has nothing left to gate (#1011). `merge-pr <N>` on one runs only
the hooks and the clean-up above, and only for a merge whose after-merge steps
are still owed: one the merge queue made — the run that enqueued it returned
first — or one a run from this clone left unconfirmed (exit 4). The clean-up
keys on the head the PR merged at, as GitHub reports it. A record in the
clone's git directory (`pkit/merge-pr/<N>.json`) says which runs owe the steps
and which ran them: a run that exits 4 records the steps as owed, and the run
that fires the hooks records that it did, so a further run from this clone does
nothing and says so. A PR merged without a queue and with nothing owed from
this clone — someone else merged it — is refused, as before. The record is the
clone's, not GitHub's: another clone finds none, and completes a PR the queue
merged by firing the hooks again, which DEC-024's idempotent hooks allow.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/merge-pr.py 99

Or via the dispatcher (per COR-021):
  pkit project-management merge-pr 99

Exit codes:
  0  merged (or dry-run reported); on a merged PR, what follows the merge ran,
     now or by an earlier run from this clone
  1  membership / merge-queue / checkbox / title / CI-status refusal; a PR
     someone else merged without a queue
  2  usage error (PR not found)
  3  gh failure: the merge failed or the queue could not be read; the PR left
     the merge queue without merging, or was taken out of it because its head
     moved
  4  accepted, a re-run from this clone completes it: the PR is in the merge
     queue and has not been seen merged, or gh accepted the merge — or a
     merge or an enqueue got no answer back — and GitHub could not be read to
     confirm it
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, merge_queue, pr_merge, session_guard
from _lib.audit import bypass_audit_key, render_ci_bypass_audit_body

# DEC-007's checkbox close-gate — the ONE implementation (`_lib.checkbox_gate`),
# shared with close-issue, done-work and the engine predicate.
from _lib.checkbox_gate import unticked_boxes as _unticked_boxes
from _lib.ci_checks import evaluate_ci_gate
from _lib.comment import post_audit_once
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.hooks import fire_hooks
from _lib.membership import (
    CAPABILITY_NAME,
    Identity,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)

# The one closing-reference reader, shared with done-work, open-pr and
# validate-pr, so every verb agrees on which issues a PR closes (#1086).
from _lib.pr_validation import extract_closing_issues as _extract_closing_issues

# The CI-bypass audit comment's first-line kind marker. It says WHAT the comment
# is; it is not what makes the post idempotent — a fixed string recognised in
# anyone's comment let a second, distinct bypass record nothing and let any
# commenter suppress the record (#902). The `_lib.audit.audit_key` writer name
# below keys the specific bypass instead.
CI_BYPASS_AUDIT_MARKER = "<!-- pkit-hook: merge-pr-ci-bypass -->"
CI_BYPASS_AUDIT_WRITER = "merge-pr-ci-bypass"

# The exit of a run whose merge was accepted and not yet seen merged (#1011):
# the merge queue holds the PR, or GitHub could not be read to confirm a merge
# gh accepted. A re-run from this clone completes it.
EXIT_ACCEPTED = 4


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Merge a PR per the methodology's merge convention: one squash "
            "commit titled after the PR, head branch deleted on merge. "
            "Enforces the checkbox close-gate on every closing issue + the "
            "PR's own body."
        ),
    )
    parser.add_argument(
        "pr_number",
        type=int,
        help="GitHub PR number to merge.",
    )
    parser.add_argument(
        "--skip-checkbox-gate",
        action="store_true",
        help=(
            "Skip the DEC-007 checkbox close-gate on closing issues. "
            "Discouraged; only when you've manually validated each box."
        ),
    )
    parser.add_argument(
        "--admin",
        action="store_true",
        help=(
            "Pass --admin to gh pr merge (bypasses branch-protection "
            "checks). Use only when authorised. Refused where the base "
            "merges through a queue: it would merge around it."
        ),
    )
    parser.add_argument(
        "--bypass-ci",
        default=None,
        help=(
            "Override the CI-status gate with an explicit reason "
            "(bypassable-with-audit per validation-severity.yaml). Posts "
            "an audit comment to the PR before merging. Use for a "
            "deliberate override — e.g. an advisory check failing on a "
            "decision-only PR. Dedicated to the CI gate; no other bypass "
            "clears a red or pending CI check. Refused where the base merges "
            "through a queue, which waits for the required checks itself."
        ),
    )
    pr_merge.add_queue_arguments(parser)
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
    if not bootstrap_gate.enforce("merge-pr", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before the PR
    # merge: target repo (cwd) vs session anchor (CLAUDE_PROJECT_DIR). How it
    # passed goes with the merge: the backbone runs its own guard on the
    # request, and is told the operator confirmed exactly when they did here.
    guard = session_guard.enforce(override=args.allow_foreign_repo)
    if not guard:
        return 1

    titles = _read_yaml(capability_root / "schemas" / "titles.yaml", yaml_loader)

    pr = _gh_get_pr(args.pr_number, config)
    if pr is None:
        return 2

    pr_title = str(pr.get("title", ""))
    pr_body = str(pr.get("body") or "")
    pr_state = str(pr.get("state", "")).lower()
    pr_url = pr.get("url") or ""

    print(f"merge-pr: #{args.pr_number}")
    print(f"  title: {pr_title}")
    print(f"  state: {pr_state}")

    base = str(pr.get("baseRefName") or "") or "the base branch"
    if pr_state == "merged":
        # A PR the queue merged after the run that enqueued it returned, or one
        # a run from this clone left unconfirmed (#1011): what follows the merge
        # is all that may be left to do.
        return _complete_merge(args, pr, base, config, capability_root)
    if pr_state != "open":
        print(
            f"\n[refused] PR is not open (state: {pr_state}). Cannot merge.",
            file=sys.stderr,
        )
        return 1

    # Whether the base merges through a queue (#1011), read before any gate so
    # a run the queue would refuse stops before it posts anything. It is read
    # again just before the merge (`pr_merge.land`).
    try:
        queue = merge_queue.read(args.pr_number, config)
        queue_refusal = pr_merge.queue_refusal(
            queue,
            base=base,
            admin=args.admin,
            bypass_ci=bool(args.bypass_ci),
            force=args.force,
            config=config,
        )
    except merge_queue.Unreadable as exc:
        print(f"error: cannot tell how {base} merges: {exc}. Nothing was merged.", file=sys.stderr)
        return 3
    if queue_refusal:
        print(f"\n{queue_refusal}", file=sys.stderr)
        return 1
    if queue.has_queue:
        print(f"  queue: {base} merges through a queue; PR #{args.pr_number} {queue.describe()}")

    # Title validation.
    title_pattern = _pr_title_pattern(titles)
    if title_pattern and not re.match(title_pattern, pr_title):
        print(
            f"\n[refused] PR title does not match Conventional Commits "
            f"pattern: {title_pattern!r}.\n"
            "  → edit the PR title (e.g., `gh pr edit <N> --title "
            "'<type>(<scope>): <summary>'`).",
            file=sys.stderr,
        )
        return 1

    # Closing-issue + PR-body checkbox gate.
    closing_issues = _extract_closing_issues(pr_body)
    print(f"  closes: {', '.join(f'#{n}' for n in closing_issues) or '<none>'}")
    if not closing_issues:
        print(
            "\n[refused] PR body has no `Closes #N` / `Fixes #N` / "
            "`Resolves #N` reference (required by git-conventions.yaml).\n"
            "  → add a `Closes #<N>` line to the PR body and retry.",
            file=sys.stderr,
        )
        return 1

    if not args.skip_checkbox_gate:
        unticked_findings = _gather_unticked_findings(
            args.pr_number, pr_body, closing_issues, config
        )
        if unticked_findings:
            print("\n[refused] DEC-007 checkbox close-gate:")
            for src, lines in unticked_findings.items():
                print(f"  {src}:")
                for line in lines:
                    print(f"    - {line}")
            print(
                "\n  → tick or remove each unticked checkbox; re-run.",
                file=sys.stderr,
            )
            return 1

    # CI-status gate (#498). A reviewer's APPROVED verdict is not evidence CI
    # passed — refuse to land a PR whose checks are red or still running. A
    # deliberate override goes through the dedicated --bypass-ci flag
    # (bypassable-with-audit): the audit comment lands on the PR first, then
    # the merge proceeds. Only --bypass-ci clears a non-green CI — no other
    # bypass silently lands a red check.
    ci_gate = evaluate_ci_gate(pr.get("statusCheckRollup"))
    if not ci_gate.passing:
        if not args.bypass_ci:
            print(
                "\n[refused] CI-status gate: the PR's checks are not all green.\n"
                f"  failing/pending: {', '.join(ci_gate.failing_checks)}\n"
                "  → wait for the checks to pass, or override this CI gate "
                'explicitly with `--bypass-ci "<reason>"` (posts an audit '
                "comment).",
                file=sys.stderr,
            )
            return 1
        if not args.bypass_ci.strip():
            print(
                "\n[refused] --bypass-ci requires a non-empty reason.",
                file=sys.stderr,
            )
            return 1
        print(
            "  ci-status: [bypass-ci] checks not green "
            f"({', '.join(ci_gate.failing_checks)}); reason: {args.bypass_ci.strip()}"
        )
    else:
        print("  ci-status: green")

    head = str(pr.get("headRefOid") or "")
    if args.dry_run:
        note = ""
        if not ci_gate.passing:
            note = " (would post CI-bypass audit comment first)"
        if queue.has_queue:
            merge = (
                f"gh pr merge {args.pr_number} --auto --match-head-commit {head[:7]} would "
                f"enqueue it{note}, then {pr_merge.wait_phrase(pr_merge.wait_seconds(args))}"
                "; once it merges, the after-merge hooks fire,"
            )
        else:
            merge = f"gh pr merge --squash --subject {pr_title!r} would be invoked{note}, then"
        print(
            f"\n[dry-run] {merge} the remote head branch deleted and the local "
            "checkout tidied; nothing written."
        )
        return 0
    if not args.yes and sys.stdin.isatty():
        question = (
            "Enqueue and, once merged, delete the head branch?"
            if queue.has_queue
            else "Squash-merge and delete the head branch?"
        )
        reply = input(f"{question} [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # Post the CI-bypass audit comment before merging so the trail survives
    # even if the merge later fails (bypassable-with-audit; the comment lands
    # first per validation-severity.yaml).
    if not ci_gate.passing and args.bypass_ci:
        if not _post_ci_bypass_audit(
            args.pr_number,
            args.bypass_ci.strip(),
            invoker,
            ci_gate.failing_checks,
            config,
            head=head,
        ):
            print(
                "[warn] could not post CI-bypass audit comment; aborting before merge.",
                file=sys.stderr,
            )
            return 3

    # The merge — or, where the base merges through a queue (#1011), the
    # enqueue and the wait for the queue's merge: `_lib.pr_merge.land`, the one
    # landing `done-work` also makes. It squash-merges with the PR title as
    # the landed subject where there is no queue (DEC-013; #33), pins the merge
    # to the head the gates read, never passes `--delete-branch` (#882), and
    # reports the PR merged only once GitHub does.
    landing = pr_merge.land(
        pr_merge.MergeRequest(
            pr_number=args.pr_number,
            pr_title=pr_title,
            head_oid=head,
            base=base,
            admin=args.admin,
            bypass_ci=bool(args.bypass_ci),
            force=args.force,
            wait_seconds=pr_merge.wait_seconds(args),
            guard_passed=session_guard.how_passed(guard),
        ),
        config,
    )
    if landing.outcome in (pr_merge.STILL_QUEUED, pr_merge.UNCONFIRMED):
        # The run returns with what follows the merge owed (exit 4): recorded,
        # so a re-run from this clone completes it however the PR merges.
        try:
            _write_record(args.pr_number, _OWED, head)
        except _Unrecorded as exc:
            print(
                f"[warn] could not record in this clone that PR #{args.pr_number}'s "
                f"after-merge steps are owed: {exc}. A later `merge-pr {args.pr_number}` "
                "completes them only if the PR merged through a merge queue.",
                file=sys.stderr,
            )
    if landing.outcome != pr_merge.MERGED:
        return _not_merged(args.pr_number, base, landing)
    print(f"\n[ok] merged: {pr_url}")
    merged_head = landing.reading.head_oid if landing.reading is not None else ""
    return _after_merge(args, pr, config, capability_root, merged_head=merged_head or head)


def _after_merge(
    args: argparse.Namespace,
    pr: dict,
    config: dict,
    capability_root: Path,
    *,
    merged_head: str,
) -> int:
    """What follows the merge: the `after_merge_pr` hooks, then the
    best-effort branch clean-up. That the hooks fired is recorded in the clone
    as soon as they have, so a later run from it fires none of them again."""
    # Fire after_merge_pr hooks per DEC-024 — FIRST, before any best-effort
    # branch cleanup, so a cleanup warning can never stand between the
    # irreversible merge and the hooks.
    fire_hooks(
        "after_merge_pr",
        context={
            "pr": {
                "number": args.pr_number,
                "title": str(pr.get("title", "")),
            },
        },
        config=config,
        capability_root=capability_root,
    )
    try:
        _write_record(args.pr_number, _RAN, merged_head)
    except _Unrecorded as exc:
        print(
            f"[warn] could not record in this clone that PR #{args.pr_number}'s after-merge "
            f"hooks fired: {exc}. A later `merge-pr {args.pr_number}` from it does not "
            "know they did.",
            file=sys.stderr,
        )

    # Branch cleanup — best-effort, never fatal. The remote head ref goes
    # through the API (no local-checkout dependency); the local steps warn
    # and continue, so a head branch checked out in a worktree (#587) is a
    # warning on the local delete, not a failed merge.
    head_branch = str(pr.get("headRefName") or "")
    if head_branch:
        # A fork PR's head name is chosen by the fork's author; never act on
        # a base-repository or local branch of that name.
        cross = bool(pr.get("isCrossRepository"))
        pr_merge.delete_remote_branch(head_branch, config, cross_repository=cross)
        pr_merge.cleanup_local(
            head_branch,
            config,
            cross_repository=cross,
            merged_head=merged_head,
        )
    else:
        print(
            "[warn] PR reports no head branch; skipping branch cleanup.",
            file=sys.stderr,
        )

    return 0


# ---- merging through a queue (#1011) ---------------------------------


def _not_merged(pr_number: int, base: str, landing: pr_merge.Landing) -> int:
    """Report a landing that did not end merged; the run's exit code.

    Accepted (exit 4) are a PR the queue was handed, and a merge GitHub could
    not then confirm — one gh accepted, or a merge or an enqueue that got no
    answer back: the run recorded the after-merge steps as owed, so
    `merge-pr` run again from this clone completes them once the PR has
    merged. Everything else merged nothing.
    """
    reading = landing.reading
    where = f" ({reading.describe()})" if reading is not None else ""
    if landing.outcome == pr_merge.STILL_QUEUED:
        if landing.message:
            print(f"[warn] {landing.message}", file=sys.stderr)
        if reading is None:
            stands = (
                f"was handed to the merge queue for {base}, and whether it has merged "
                "since could not be read"
            )
        else:
            stands = f"is in the merge queue for {base}{where} and has not merged yet"
        print(
            f"\n[queued] PR #{pr_number} {stands}. Run `merge-pr {pr_number}` again once "
            "it has merged: it fires the after-merge hooks and cleans up the branch."
        )
        return EXIT_ACCEPTED
    if landing.outcome == pr_merge.UNCONFIRMED:
        print(
            f"\n[unconfirmed] {landing.message}. Nothing after the merge has run. Run "
            f"`merge-pr {pr_number}` again from this clone once GitHub answers: if the PR "
            "merged, it fires the after-merge hooks and cleans up the branch; if it did "
            "not, it merges it."
        )
        return EXIT_ACCEPTED
    if landing.outcome == pr_merge.REFUSED:
        print(f"\n{landing.message}", file=sys.stderr)
        return 1
    if landing.outcome == pr_merge.UNREADABLE:
        print(f"error: {landing.message}. Nothing was merged.", file=sys.stderr)
        return 3
    if landing.outcome == pr_merge.HEAD_MOVED:
        print(
            f"error: {landing.message} Once the new commits have been checked, re-run "
            f"`merge-pr {pr_number}`.",
            file=sys.stderr,
        )
    elif landing.outcome == pr_merge.LEFT:
        print(
            f"error: PR #{pr_number} has not merged, as far as GitHub reports{where}: "
            f"if the merge queue for {base} dropped it, its checks may have failed on "
            "the merge it was about to make, or it no longer merged cleanly onto what "
            f"merged ahead of it. Nothing after the merge ran; fix the branch if it "
            f"needs it, then re-run `merge-pr {pr_number}`.",
            file=sys.stderr,
        )
    return 3


def _complete_merge(
    args: argparse.Namespace,
    pr: dict,
    base: str,
    config: dict,
    capability_root: Path,
) -> int:
    """What follows the merge, for a PR that has merged already (#1011).

    The run that merged or enqueued it returned before it saw the merge
    (exit 4), so its gates ran then and only the hooks and the clean-up are
    left — once. They are owed for a PR the merge queue merged, and for one
    this clone's record says a run left owed; the clean-up keys on the head the
    PR merged at, as GitHub reports it. Once this clone's record says the hooks
    fired, the run does nothing and says so. A PR merged without a queue and
    owed nothing here was merged by someone else, and is refused as before.
    """
    number = args.pr_number
    record = _read_record(number)
    if record is not None and record.state == _RAN:
        when = f" at {record.at}" if record.at else ""
        print(
            f"\n[ok] PR #{number} has merged, and its after-merge hooks already fired "
            f"from this clone{when}; nothing is left to do."
        )
        return 0
    try:
        reading = merge_queue.read(number, config)
    except merge_queue.Unreadable as exc:
        print(
            f"error: cannot tell how PR #{number} merged: {exc}. Nothing was changed.",
            file=sys.stderr,
        )
        return 3
    if reading.ever_queued:
        print(
            f"  PR #{number} merged through the merge queue for {base} "
            f"({reading.describe()}); completing what follows the merge"
        )
    elif record is not None and record.state == _OWED:
        print(
            f"  PR #{number} merged ({reading.describe()}), and a run from this clone "
            "returned before it saw the merge; completing what follows the merge"
        )
    else:
        print(
            f"\n[refused] PR #{number} merged without going through a merge queue, by "
            "someone else as far as this clone knows: no run from it left anything after "
            "that merge to complete. Nothing was run.",
            file=sys.stderr,
        )
        return 1
    if args.dry_run:
        print(
            "\n[dry-run] the after-merge hooks would fire, then the remote head branch "
            "be deleted and the local checkout tidied; nothing written."
        )
        return 0
    if not args.yes and sys.stdin.isatty():
        reply = input("Fire the after-merge hooks and delete the head branch? [y/N] ")
        if reply.strip().lower() not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0
    return _after_merge(
        args,
        pr,
        config,
        capability_root,
        merged_head=reading.head_oid or str(pr.get("headRefOid") or ""),
    )


# ---- the clone's record of what follows a merge (#1011) ----------------
#
# GitHub records whether a PR merged and whether it went through a queue, but
# not whether merge-pr's after-merge steps ran, nor that a run of it left them
# owed. The clone keeps that, one small file per PR in its git directory. A
# comment on the PR would be a governed act's projection, which the default
# audit level does not post (DEC-049).

# The record's two states: a run returned with the after-merge steps owed
# (exit 4); a run fired the after-merge hooks.
_OWED = "owed"
_RAN = "ran"


@dataclass(frozen=True)
class _Record:
    state: str
    #: The PR head the run gated (owed) or the PR merged at (ran).
    head_oid: str = ""
    #: When it was recorded, UTC, ISO 8601.
    at: str = ""


class _Unrecorded(Exception):
    """The record could not be written; the message says why."""


def _record_path(pr_number: int) -> Path | None:
    """Where the clone keeps PR `pr_number`'s record, under its common git
    directory so every worktree of the clone shares it; None outside a clone."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    common = proc.stdout.strip()
    if proc.returncode != 0 or not common:
        return None
    return Path(common).resolve() / "pkit" / "merge-pr" / f"{pr_number}.json"


def _read_record(pr_number: int) -> _Record | None:
    """The clone's record for PR `pr_number`, or None when it has none it can read."""
    path = _record_path(pr_number)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("state") not in (_OWED, _RAN):
        return None
    return _Record(str(data["state"]), str(data.get("head") or ""), str(data.get("at") or ""))


def _write_record(pr_number: int, state: str, head_oid: str) -> None:
    """Record `state` for PR `pr_number` in the clone. Raises
    :class:`_Unrecorded` when it cannot be written."""
    path = _record_path(pr_number)
    if path is None:
        raise _Unrecorded("not inside a git clone")
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"state": state, "head": head_oid, "at": at}) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise _Unrecorded(str(exc)) from exc


# ---- closing-issue checkbox sweep ----------------------------------


def _gather_unticked_findings(
    pr_number: int, pr_body: str, closing_issues: list[int], config: dict
) -> dict[str, list[str]]:
    """Return a mapping of source label → unticked-box lines.

    Sources: 'PR body' for the PR's own body, '#<N>' for each closing
    issue.
    """
    findings: dict[str, list[str]] = {}
    pr_unticked = _unticked_boxes(pr_body)
    if pr_unticked:
        findings["PR body"] = pr_unticked
    for n in closing_issues:
        issue = _gh_get_issue(n, config)
        if issue is None:
            findings[f"#{n}"] = ["(could not fetch issue body)"]
            continue
        body = str(issue.get("body") or "")
        unticked = _unticked_boxes(body)
        if unticked:
            findings[f"#{n}"] = unticked
    return findings


# ---- schema helpers ------------------------------------------------


def _pr_title_pattern(titles: dict) -> str | None:
    formats = titles.get("formats") or {}
    entry = formats.get("pr")
    if isinstance(entry, dict):
        p = entry.get("pattern")
        if isinstance(p, str):
            return p
    return None


# ---- CI-bypass audit -------------------------------------------------


def _ci_bypass_audit_key(reason: str, head: str) -> str:
    """The CI-bypass idempotency key (#902) — the shared
    `_lib.audit.bypass_audit_key`: the stripped reason and the PR head commit."""
    return bypass_audit_key(CI_BYPASS_AUDIT_WRITER, reason, head)


def _ci_bypass_audit_body(
    invoker: Identity,
    reason: str,
    failing_checks: tuple[str, ...],
    key: str,
    head: str = "",
) -> str:
    """Render the CI-bypass audit comment — the shape shared with `done-work`
    (`_lib.audit.render_ci_bypass_audit_body`) under this script's kind marker."""
    return render_ci_bypass_audit_body(
        CI_BYPASS_AUDIT_MARKER,
        invoker,
        reason,
        failing_checks,
        head,
        key,
    )


def _post_ci_bypass_audit(
    pr_number: int,
    reason: str,
    invoker: Identity,
    failing_checks: tuple[str, ...],
    config: dict,
    *,
    head: str = "",
) -> bool:
    """Post the CI-bypass audit comment to the PR, once per (reason, head).

    Returns True on success (or when this exact comment is already present),
    False on gh failure. The post-once rule is the shared
    `_lib.comment.post_audit_once` (#902).
    """
    key = _ci_bypass_audit_key(reason, head)
    return post_audit_once(
        "pr",
        pr_number,
        key,
        _ci_bypass_audit_body(invoker, reason, failing_checks, key, head),
        config,
        run=gh_run,
        present_note="ci-bypass audit comment already present; idempotent skip",
        posted_note="ci-bypass audit comment posted",
    )


# ---- gh wrappers ----------------------------------------------------


def _gh_get_pr(pr_number: int, config: dict) -> dict | None:
    try:
        proc = gh_run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "title,body,state,url,headRefName,headRefOid,baseRefName,statusCheckRollup,isCrossRepository",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: gh pr view {pr_number} failed.\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(issue_number, config, fields="title,body,state")


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
