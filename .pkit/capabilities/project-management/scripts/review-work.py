#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — review-work (DEC-026 workflow wrapper).

Transitions an issue In Progress → Review by opening a ready PR (or
flipping a draft PR to ready) and assigning reviewers. Per DEC-026:

    review-work <N> [--reviewer @<user>] [--require-human] [--bypass-owner "<reason>"]

Gates per DEC-026:
  - Membership (open-mode degrades to no-op).
  - The issue's branch is a local one matching `<type>/<N>-<slug>` AND its
    `<type>` matches the issue's `type:*` label per DEC-013. Of several
    matching, the one with the issue's open PR; with none or more than one
    open, it refuses, naming each (`_lib/issue_branch`, #1608).
  - Issue's current state can move to Review per workflow.yaml (or is
    already there, so a re-run works). Checked before any PR is opened or
    flipped ready and before reviewers are requested, so a refused move
    leaves the PR as it was (#947). From Backlog, move to In Progress first.
    The state is read from the issue's labels and milestone
    (`_lib/issue_position`, shared with start-work, #1242); move-issue reads
    it itself when it moves.
  - PR title is Conventional Commits.
  - The author's sentences (DEC-065 point 3): each document the change check
    marks `updated` at the PR's head needs a sentence on what changed in it,
    under the description's `## What changed in each updated document`. The
    check is run at the PR's head on every move (`friction_answers.checked`, the
    head fetched first where this clone lacks it), since the description carries
    no list of the answers. The description is read, a draft's or a ready PR's,
    before the PR is made ready, reviewers are requested or the issue moves.
    Refused at validate-at-ready's severity, hard-reject, naming each such
    document, the form a sentence takes and each item there that is not read as
    one. Each sentence that reads as a closing reference is refused the same way:
    the host would close an issue with it at merge (DEC-065 point 5). Each sentence
    on a document the check does not mark `updated` gets a warning naming the edit
    that removes it, as open-pr and land-work give it. A
    check that cannot be run at the head stops the run (exit 2), and so does a
    description that cannot be read (exit 3): nothing is refused on either.
    Under `--force`, a check that cannot be run refuses nothing, with a warning,
    and a refusal is printed and overridden, and the audit comment below names
    either. open-pr warns of a missing sentence; edit-pr derives nothing and
    warns of none.
  - The clash guard (DEC-035 point 6), with an instance id set or a seat of
    a topology held: an issue another instance owns is refused before any PR
    is opened or made ready and before reviewers are requested, at
    bypassable-with-audit (DEC-014), through `_lib/instance_claims`.
    `--bypass-owner "<reason>"` posts the reason on the issue as an audit
    comment first, and the composed move-issue is handed the same reason, so
    it posts no second one. The flag is qualified per DEC-046, since the
    validate-at-ready stop is a second gate: it refuses a finding declared
    bypassable-with-audit as it refuses a hard-reject one, and `--force`
    writes past it. In a project with a topology, a claim whose clone no
    longer holds its seat is no claim, and one that cannot be judged refuses
    (DEC-059 point 9). Before the guard, a clone that took a seat confirms it
    on the seat's state issue, and the command refuses where it cannot
    (DEC-059 point 6).

Side-effects:
  - Opens a ready PR via `gh pr create` if none exists for the branch.
  - Flips an existing draft PR to ready via `gh pr ready` if present.
  - Reviewer assignment (v1 ships with simple --reviewer override path;
    full DEC-027 mode resolution lands in Phase D).
  - Under `--force`, one audit comment on the PR names who gave the override
    and each refusal it passed, a change check it could not run at the head
    among them (DEC-046 point 2). Its first lines are the audit template's
    (`_lib.audit.render_audit_comment`), and it goes through `post_audit_once`,
    so a retry of the same override at the same head posts no second one. It
    lands before the PR is made ready, reviewers are requested or the issue
    moves; on a PR this run opens, as soon as the PR exists. One that cannot be
    posted stops the run. At `audit.projection: off` none is posted (DEC-049
    point 2), and the override shows in the output only.
  - A document's path, the words of a description and what the change check
    said at the head are the head's text. Each character a terminal would act
    on is written as its escape wherever a line shows them (`_said`), and the
    comment quotes them in code spans with no `<!--` (`_quoted`).
  - Composes over `move-issue.py --to review`. If that move still fails
    after the PR was opened or flipped ready (a network error, or a state
    that changed since the check so the move is no longer legal), the run
    ends on a failure naming what it left behind: the PR, its ready state and
    the reviewers it requested.

Exit codes:
  0  PR ready + issue in Review (moved there, or already there)
  1  membership or foreign-repo refusal / PR body not ready for review
     (validate-at-ready, an updated document with no sentence, or a sentence that
     reads as a closing reference; --force overrides) / the clash guard refused an
     issue another instance owns /
     this clone's seat could not be confirmed
  2  usage error / gate failure / illegal transition / issue not found /
     where the board carries the state, a card whose Status does not place
     the issue / the change check could not be run at the PR's head
  3  gh failure: `gh pr create` could not open the PR, the PR's description
     could not be read, `gh pr ready` could not make it ready, the audit comment
     of a --force could not be posted, or the board carrying the state could
     not be read
  *  a failed composed move-issue passes its exit code through
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    axis_labels,
    bootstrap_gate,
    classification_rules,
    composed_move,
    default_branch,
    friction_answers,
    instance_claims,
    issue_branch,
    issue_position,
    pr_validation,
    session_guard,
)
from _lib import lifecycle_inference as infer
from _lib.audit import (
    PROJECTION_OFF,
    audit_key,
    audit_projection,
    render_audit_comment,
    short_sha,
)
from _lib.audit_log import code
from _lib.comment import post_audit_once
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    Identity,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.placeholder_detection import PHASE_TRANSITION
from _lib.review_mode import (
    resolve_mode,
    reviewer_role_from_config,
    role_based_reviewers,
)

TARGET_STATE = "review"
#: What to do about a refused body when no PR is open yet.
FILL_FIRST = (
    "fill the body first (create-draft → edit-pr → review-work), or use open-pr --body-file"
)
#: The label of a finding on the author's sentences, as edit-pr's validation names it.
SENTENCES_LABEL = "body.sentences"


#: The exit where the change check could not be run at the PR's head.
EXIT_UNDERIVED = 2

#: The `_lib.audit.audit_key` writer name of the audit comment a `--force` leaves.
FORCE_AUDIT_WRITER = "review-work-force"
#: How a line names a stop that is no finding: a script precondition (DEC-046
#: point 2), here a change check that could not be run at the PR's head. It blocks
#: nothing, since only `--force` goes on past that stop.
PRECONDITION = "precondition"
#: What `--force` passes and its audit comment names. A warning refuses nothing.
OVERRIDDEN = (*pr_validation.BLOCKING_SEVERITIES, PRECONDITION)


@dataclass(frozen=True)
class _Description:
    """A PR's description, with the PR's number, its head, its base branch and the
    branch it is opened from as GitHub names them, and whether it comes from a
    fork: what the author's sentences are checked against, and where the head is
    fetched from. A body review-work composes for a PR not opened yet has none of
    them."""

    body: str
    number: int | None = None
    head: str = ""
    base: str = ""
    branch: str = ""
    cross_repository: bool = False


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Open or flip-ready a PR for an issue; transition issue "
            "In Progress → Review. Composes over move-issue per DEC-026."
        ),
    )
    parser.add_argument("issue_number", type=int)
    parser.add_argument(
        "--reviewer",
        action="append",
        default=[],
        help="Reviewer to assign (repeatable). May be a @user, user, or team.",
    )
    parser.add_argument(
        "--require-human",
        action="store_true",
        help=(
            "Force human-mode review even when project config defaults to "
            "agent mode. (Phase D — DEC-027 — wires the full mode-resolution "
            "algorithm; this flag is a v1 forward-compat placeholder.)"
        ),
    )
    parser.add_argument(
        "--base",
        default=None,
        help=(
            "Base branch for a newly opened PR (default: the issue's DEC-013 "
            "integration branch when its body carries an `Integration:` marker, "
            "else the project's default branch — the backbone's "
            "`repository.default-branch`, COR-054). Not applied to an existing PR."
        ),
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Take a PR to ready-for-review despite hard-reject body-validation "
            "findings (empty required section / checkbox / missing Doc impact / an "
            "updated document with no sentence on what changed in it) or a change "
            "check that cannot be run at its head. One audit comment on the PR names "
            "who gave the override and each refusal it passed. "
            "Drafts stay exempt; you normally fill a draft first (create-draft → "
            "edit-pr → review-work) or use open-pr --body-file."
        ),
    )
    parser.add_argument(
        "--bypass-owner",
        default=None,
        metavar="REASON",
        help=(
            "Bypass the clash guard, which refuses an issue another instance owns "
            "(bypassable-with-audit per DEC-014, DEC-035 point 6): the reason is "
            "posted on the issue as an audit comment before any PR is opened or "
            "made ready. Qualified per DEC-046, since the validate-at-ready stop "
            "is a second gate, which --force writes past."
        ),
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("review-work", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    classification = _read_classification(capability_root, yaml_loader)
    workflow = _read_schema(capability_root, "workflow.yaml", yaml_loader)
    issue_types = _read_schema(capability_root, "issue-types.yaml", yaml_loader)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before the PR
    # reviewer write / composed move-issue. A confirmed override threads into
    # move-issue so the gate is confirmed once, not twice.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    # Find the issue's local branch (#1608): of several, the one with its open PR.
    reading = issue_branch.read(args.issue_number, config)
    if reading.refusal:
        print(f"error: {reading.refusal}", file=sys.stderr)
        return 2
    branch = reading.branch
    if branch is None:
        print(
            f"error: no local branch matching `*/{args.issue_number}-*` found.",
            file=sys.stderr,
        )
        return 2

    # Fetch issue for type-label cross-check + title derivation.
    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2
    title = str(issue.get("title", ""))
    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    substrate_map = axis_labels.load_substrate_map(capability_root)

    # Gate: the move to Review is legal from where the issue is (#947). Asked
    # before the PR is opened or flipped ready and before reviewers are
    # requested, so a refusal changes nothing. The state is read as
    # start-work's gate reads it (#942, #1242): where the board carries it, from
    # the card's Status, and a Status that does not place the issue refuses, a
    # board that cannot be read as the gh failure it is (DEC-051 point 6).
    status = issue_position.read_status(args.issue_number, issue, config, substrate_map, workflow)
    current = issue_position.current_state(issue, labels, substrate_map, status)
    if current == infer.UNDETERMINED:
        print(
            issue_position.unplaced_refusal(
                "review-work",
                args.issue_number,
                status,
                untouched="no PR opened or made ready, no reviewers requested",
            ),
            file=sys.stderr,
        )
        return 3 if status is None or status.outcome == "unreadable" else 2
    refusal = composed_move.transition_refusal(
        "review-work",
        args.issue_number,
        issue,
        labels,
        current,
        target=TARGET_STATE,
        untouched="no PR opened or made ready, no reviewers requested",
        workflow=workflow,
        issue_types=issue_types,
        classification=classification,
    )
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return 2

    expected_prefix = _derive_branch_prefix(labels, title, classification, substrate_map)
    branch_prefix_match = re.match(r"^([a-z]+)/", branch)
    branch_prefix = branch_prefix_match.group(1) if branch_prefix_match else None
    if expected_prefix and branch_prefix and expected_prefix != branch_prefix:
        print(
            f"error: branch prefix {branch_prefix!r} doesn't match the issue's "
            f"type:* label (expected `{expected_prefix}` per DEC-013).",
            file=sys.stderr,
        )
        return 2

    # Base branch (DEC-013, #903): --base, else the issue's integration marker,
    # else default_branch — the resolution start-work cut the branch by.
    try:
        base = infer.resolve_base_branch(config, str(issue.get("body") or ""), explicit=args.base)
    except default_branch.Unanswered as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # The clash guard (DEC-035 point 6), before the PR is opened or made ready
    # and before reviewers are requested: an issue another instance owns is
    # refused, unless a bypass posts its reason. The move this run composes is
    # handed the same reason, and finds its audit comment posted.
    # A seat is confirmed on its state issue first (DEC-059 point 6).
    owner_bypass: str | None = None
    try:
        clone = instance_claims.this_clone(
            capability_root, invoker.github_login, config, dry_run=args.dry_run
        )
    except instance_claims.Unconfirmed as exc:
        return instance_claims.say_unconfirmed("review-work", args.issue_number, exc)
    if clone is not None:
        decision = instance_claims.guard(
            args.issue_number,
            clone,
            config,
            verb="review-work",
            flag="--bypass-owner",
            bypass=args.bypass_owner,
            invoker=invoker,
            dry_run=args.dry_run,
        )
        instance_claims.say_guard(decision)
        if decision.refused:
            return 1
        if decision.bypassed:
            owner_bypass = args.bypass_owner

    print(f"review-work: #{args.issue_number}")
    print(f"  branch: {branch}")
    print(f"  base:   {base}")

    if args.dry_run:
        print("(dry-run: would open/flip-ready PR, assign reviewers, call move-issue.)")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # PR handling: open ready, or flip draft → ready. Validate-at-ready (#569):
    # a PR going ready-for-review must pass the checks the merge gate enforces
    # (DEC-031 empty checkbox → hard-reject; DEC-015 Doc impact). Drafts are
    # exempt; --force overrides. An empty body cannot go ready — fill a draft
    # first (create-draft → edit-pr → review-work), or use open-pr --body-file.
    # A description that gives no sentence on what changed in a document the
    # change check marks updated at the PR's head is refused too, a PR already
    # ready included, before reviewers are requested or the issue moves (DEC-065
    # point 3).
    existing_pr = _find_pr_for_branch(branch, config)
    pr_number: int | None = None
    # What this run changed on the PR, named if the composed move then fails.
    opened_url: str | None = None
    flipped = False
    if existing_pr is None:
        # Open a ready PR (non-draft) — validate the composed body first.
        title = _derive_pr_title(issue, branch)
        body = f"Closes #{args.issue_number}"
        # The body composed here has no sentences and no `## Doc impact`, so
        # validate-at-ready refuses it unless --force passes it, which would pass a
        # missing sentence too: no answers are derived for it.
        findings = _ready_findings(body, classification, capability_root)
        if not _body_ok(findings, args.force, next_step=FILL_FIRST):
            return 1
        url = _gh_pr_create_ready(branch, base, title, body, config)
        if url is None:
            return 3
        m = re.search(r"/pull/(\d+)", url)
        pr_number = int(m.group(1)) if m else None
        opened_url = url
        print(f"  opened ready PR: {url}")
        # The first moment the PR exists, so the one write this comment follows.
        if not _force_audited(
            pr_number, findings, "", capability_root, invoker, config, opened_url=url
        ):
            return 3
    elif existing_pr.get("isDraft"):
        # Flip draft → ready — validate the draft's current body first.
        pr_number = existing_pr.get("number")
        description = _gh_pr_description(pr_number, config)
        if description is None:
            return 3
        sentences = _sentence_findings(description, force=args.force)
        if sentences is None:
            return EXIT_UNDERIVED
        findings = _ready_findings(description.body, classification, capability_root) + sentences
        if not _body_ok(findings, args.force, next_step=_edit_step(args.issue_number, pr_number)):
            return 1
        if not _force_audited(
            pr_number, findings, description.head, capability_root, invoker, config
        ):
            return 3
        if not _gh_pr_ready(pr_number, config):
            return 3
        flipped = True
        print(f"  flipped PR #{pr_number} draft → ready")
    else:
        pr_number = existing_pr.get("number")
        description = _gh_pr_description(pr_number, config)
        if description is None:
            return 3
        sentences = _sentence_findings(description, force=args.force)
        if sentences is None:
            return EXIT_UNDERIVED
        if not _body_ok(sentences, args.force, next_step=_edit_step(args.issue_number, pr_number)):
            return 1
        if not _force_audited(
            pr_number, sentences, description.head, capability_root, invoker, config
        ):
            return 3
        print(f"  PR #{pr_number} already ready; idempotent skip")

    # Reviewer assignment per DEC-027 mode resolution.
    mode_resolution = resolve_mode(
        config,
        issue_labels=labels,
        require_human=args.require_human,
    )
    print(f"  mode:   {mode_resolution.mode} ({mode_resolution.source})")

    reviewers_to_add = list(args.reviewer)  # explicit --reviewer overrides
    if mode_resolution.mode == "human" and not reviewers_to_add:
        members = _read_members(capability_root, yaml_loader)
        role = reviewer_role_from_config(config)
        if role:
            candidates = role_based_reviewers(
                members,
                role,
                exclude_login=invoker.github_login,
            )
            if candidates:
                reviewers_to_add = candidates
                print(
                    f"  human-mode reviewers (role={role}): "
                    f"{', '.join('@' + r for r in candidates)}"
                )
            else:
                print(
                    f"  [warn] human mode but no eligible reviewers for role={role!r}.",
                    file=sys.stderr,
                )
        else:
            print(
                "  [warn] human mode but `review.human_review.reviewer_role:` not set.",
                file=sys.stderr,
            )

    reviewers_requested: list[str] = []
    if pr_number is not None and reviewers_to_add:
        if _gh_pr_add_reviewers(pr_number, reviewers_to_add, config):
            reviewers_requested = [r.lstrip("@") for r in reviewers_to_add]
        else:
            print(
                "[warn] PR ready but reviewer assignment failed; assign manually.",
                file=sys.stderr,
            )

    # Compose over move-issue for the state transition.
    rc = composed_move.invoke_move_issue(
        args.issue_number,
        TARGET_STATE,
        capability_root_arg=args.capability_root,
        allow_foreign_repo=args.allow_foreign_repo,
        **({"bypass_owner": owner_bypass} if owner_bypass else {}),
    )
    if rc != 0:
        print(
            composed_move.late_failure_message(
                "review-work",
                args.issue_number,
                TARGET_STATE,
                rc,
                left=_left_behind(
                    pr_number=pr_number,
                    opened_url=opened_url,
                    flipped=flipped,
                    reviewers=reviewers_requested,
                ),
                nothing_left="This run opened no PR, made none ready and requested no reviewers.",
                reuses="the ready PR",
            ),
            file=sys.stderr,
        )
        return rc

    print(_success_line(args.issue_number, workflow))
    return 0


# ---- helpers -----------------------------------------------------------


def _derive_branch_prefix(
    labels: list[str],
    title: str,
    classification: dict,
    substrate_map: axis_labels.SubstrateMap | None,
) -> str | None:
    """The conventional-commit prefix the branch is validated against (DEC-013).

    Resolves the kit type *value* through the ADR-026 read seam, then maps it to
    the conv-type via classification.yaml's `pr_type_mapping` — identical to
    start-work's derivation (both read the one shared table, per COR-007):

    * label substrate ⇒ `axis_labels.resolve_read("type", labels, substrate_map)`
      — the kit's `type:*` label in greenfield, the adopter's remapped label
      under a `label` binding (#910);
    * brownfield `title-prefix` substrate ⇒ `classification_rules.kind_from_title`,
      where no `type:*` label exists to read.

    The label arm is tried first so greenfield stays byte-identical. `None` when
    neither arm resolves a recognised value — the caller then skips the
    prefix/branch cross-check rather than failing on an underivable type."""
    kind = axis_labels.resolve_read("type", labels, substrate_map)
    if kind is None:
        kind = classification_rules.kind_from_title(title, classification)
    if kind is None:
        return None
    return classification_rules.conv_type_for_kind(kind, classification)


def _derive_pr_title(issue: dict, branch: str) -> str:
    title = re.sub(r"^\[[^\]]+\]\s*", "", str(issue.get("title", "")))
    prefix_match = re.match(r"^([a-z]+)/", branch)
    prefix = prefix_match.group(1) if prefix_match else "feat"
    return f"{prefix}: {title}".strip()


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    """The issue, with the fields the early check reads its card by
    (`issue_position.ISSUE_FIELDS`)."""
    fields = f"title,labels,body,state,milestone,{issue_position.ISSUE_FIELDS}"
    return gh_get_issue(issue_number, config, fields=fields)


def _left_behind(
    *,
    pr_number: int | None,
    opened_url: str | None,
    flipped: bool,
    reviewers: list[str],
) -> list[tuple[str, str]]:
    """What this run changed before the composed move-issue failed, each with
    its undo: the PR it opened ready or flipped from draft to ready, and the
    reviewers it requested. A PR that was already ready is not something this
    run left behind."""
    left: list[tuple[str, str]] = []
    if opened_url is not None:
        pr = f"PR #{pr_number} ({opened_url})" if pr_number is not None else f"PR {opened_url}"
        pr_arg = str(pr_number) if pr_number is not None else opened_url
        left.append((f"{pr}, opened ready for review", f"gh pr close {pr_arg}"))
    elif flipped:
        left.append(
            (
                f"PR #{pr_number}, flipped from draft to ready for review",
                f"gh pr ready {pr_number} --undo",
            )
        )
    if reviewers:
        left.append(
            (
                f"review requested from {', '.join('@' + r for r in reviewers)} on PR #{pr_number}",
                f"gh pr edit {pr_number} --remove-reviewer {','.join(reviewers)}",
            )
        )
    return left


def _success_line(issue_number: int, workflow: dict) -> str:
    """The closing line of a run whose move-issue succeeded: the PR is ready
    and the issue in Review. It claims no move. move-issue reads the state
    itself when it moves, so only its own output, just above, says whether it
    moved the issue or found it already in Review."""
    review = infer.state_display_name(workflow, TARGET_STATE)
    return f"\n[ok] PR ready; #{issue_number} in {review}"


def _find_pr_for_branch(branch: str, config: dict) -> dict | None:
    proc = gh_run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "all",
            "--json",
            "number,state,isDraft,headRefName",
        ],
        config,
        check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        prs = json.loads(proc.stdout)
        for pr in prs:
            if pr.get("headRefName") == branch and pr.get("state") == "OPEN":
                return pr
    except (ValueError, KeyError):
        pass
    return None


def _gh_pr_create_ready(branch: str, base: str, title: str, body: str, config: dict) -> str | None:
    proc = gh_run(
        ["gh", "pr", "create", "--head", branch, "--base", base, "--title", title, "--body", body],
        config,
        check=False,
    )
    if proc.returncode != 0:
        print(f"error: gh pr create failed: {proc.stderr.strip()}", file=sys.stderr)
        return None
    return proc.stdout.strip()


def _ready_findings(
    body: str, classification: dict, capability_root: Path
) -> list[pr_validation.Finding]:
    """Validate-at-ready (#569): each finding that keeps `body` from going
    ready-for-review.

    Runs the shared PR-body validator at the merge-gate phase (empty checkbox →
    hard-reject). Title/closing-label checks are skipped (review-work composes the
    title). The findings on the author's sentences join these
    (`_sentence_findings`), so one refusal names every blocking finding. Merge
    remains the backstop; drafts never reach here.
    """
    findings = pr_validation.validate_pr(
        pr_title="",
        pr_body=body,
        titles={},
        classification=classification,
        git_conv={},
        closing_type_labels=[],
        capability_root=capability_root,
        phase=PHASE_TRANSITION,
    )
    return [f for f in findings if f.severity in pr_validation.BLOCKING_SEVERITIES]


def _sentence_findings(
    description: _Description, *, force: bool = False
) -> list[pr_validation.Finding] | None:
    """A hard-reject finding for each document the change check marks `updated` at
    the PR's head that the PR's description gives no sentence on what changed in it
    (DEC-065 point 3), named with the form a sentence takes, and for each sentence
    that reads as a closing reference (DEC-065 point 5). Each item under the
    sentences heading that is not read as one follows a missing sentence, as a
    warning: it is likely the sentence, in another form. Nothing where every such
    document has a sentence and none reads so.

    The answers are derived at the PR's head on every move (`_unsaid_at_head`); the
    description carries none. None, with what failed printed, where they cannot be
    derived there: nothing is refused on answers nobody read. Under ``force``
    nothing is refused then either, with a warning saying so, and the stop it passed
    is the one finding, for its audit comment to name (`PRECONDITION`)."""
    unsaid, underived = _unsaid_at_head(description)
    if underived:
        return _underived_findings(underived, force)
    refused = [
        pr_validation.Finding(
            pr_validation.SEVERITY_HARD_REJECT,
            SENTENCES_LABEL,
            message,
        )
        for message in (
            *(friction_answers.unsaid_message(location) for location in unsaid),
            *(
                friction_answers.closing_message(*found)
                for found in friction_answers.closing_references(
                    friction_answers.sentences(description.body)
                )
            ),
        )
    ]
    unread = [
        pr_validation.Finding(
            pr_validation.SEVERITY_WARNING,
            SENTENCES_LABEL,
            friction_answers.unread_warning(item),
        )
        for item in (friction_answers.unread(description.body) if unsaid else ())
    ]
    return refused + unread


def _unsaid_at_head(description: _Description) -> tuple[list[str], str]:
    """Each document the change check marks `updated` at the PR's head that the
    description gives no sentence for, in the check's order, and why the check could
    not be run there, empty where it ran. Each sentence on a document the check does
    not mark `updated` gets a warning, as open-pr and land-work give it: no reviewer
    checks it. Only the answers are read, not the friction settings
    (`friction_answers.checked`), and the head is fetched first where this clone
    lacks it."""
    body = description.body
    head, number = description.head, description.number
    problem = ""
    if not head or number is None:
        problem = f"GitHub named no head for PR #{number}"
    elif not description.base:
        problem = f"GitHub named no base branch for PR #{number}"
    else:
        source = (
            friction_answers.pull_request_source(
                description.branch,
                number,
                cross_repository=description.cross_repository,
                base=description.base,
            )
            if description.branch or description.cross_repository
            else None
        )
        derived = friction_answers.checked(head, description.base, source=source)
        if derived.document is not None:
            said = friction_answers.sentences(body)
            for location in friction_answers.unlisted(derived.document, said):
                warning = friction_answers.unlisted_warning(location, head, number)
                print(f"  [warn] {friction_answers.shown(warning)}", file=sys.stderr)
            return friction_answers.unsaid(derived.document, said), ""
        problem = derived.problem or "the change check gave no document"
    return [], (
        f"the change check at PR #{number}'s head {_commit(head)} could not be run ({problem})"
    )


def _underived_findings(underived: str, force: bool) -> list[pr_validation.Finding] | None:
    """What a change check that could not be run at the PR's head, `underived`, comes
    to. None, with the stop printed. Under ``force``, a warning saying the sentences
    went unchecked, and the stop as a `PRECONDITION` for the audit comment."""
    said = friction_answers.shown(underived)
    if force:
        print(
            f"  [warn] {said}; under --force, no sentence on what changed is checked, "
            "and the move goes on.",
            file=sys.stderr,
        )
        return [pr_validation.Finding(PRECONDITION, SENTENCES_LABEL, underived)]
    print(
        f"error: {said}, so which documents need a sentence cannot be told. Nothing was "
        "made ready, no reviewer requested and the issue not moved. Run review-work again once "
        "it can be run.",
        file=sys.stderr,
    )
    return None


def _commit(oid: str) -> str:
    """A head as a line names it: its short form, or that none is named."""
    return oid[: friction_answers.SHORT] or "a head it does not name"


def _edit_step(issue_number: int, pr_number: int | None) -> str:
    """What to do about a refused description of PR `pr_number`: write it with
    edit-pr, then run review-work again."""
    return (
        f"write the description with `edit-pr {pr_number} --body-file <file>`, then run "
        f"`review-work {issue_number}` again"
    )


def _body_ok(findings: list[pr_validation.Finding], force: bool, *, next_step: str) -> bool:
    """True iff no finding of `findings` blocks; otherwise print them all, with
    `next_step`, and return False, or True under ``force``. The findings are
    validate-at-ready's (#569) and the author's sentences' (DEC-065 point 3)."""
    if not pr_validation.has_blocking(findings):
        return True
    print("[refused] PR body is not ready for review:", file=sys.stderr)
    for f in findings:
        print(f"  - {_said(f)}", file=sys.stderr)
    if force:
        print("  → proceeding under --force.", file=sys.stderr)
        return True
    print(f"  → {next_step}; --force overrides.", file=sys.stderr)
    return False


def _said(finding: pr_validation.Finding) -> str:
    """`finding` as a line says it, each character a terminal would act on written
    as its escape: a finding can carry the head's text, so a document's path or the
    words of a description never move the cursor or start a line of their own."""
    return friction_answers.shown(f"[{finding.severity}] {finding.label}: {finding.detail}")


def _quoted(finding: pr_validation.Finding) -> str:
    """`finding` as its audit comment quotes it: `_said`, in a code span, where a
    mention, a link and an HTML comment are not live. A `<!--` is written as its
    escape too, since some readers of a PR's comments find their marker anywhere in
    the text, a code span included."""
    return code(_said(finding).replace("<!--", "\\x3c!--"))


def _force_audit_body(
    quoted: list[str], head: str, key: str, capability_root: Path, invoker: Identity
) -> str:
    """The audit comment of a `--force`: the template's line, which names who gave
    the override, then each refusal it passed, `quoted`, below it, where `_lib.audit`
    has a writer add what the template has no field for, then the idempotency `key`.
    `head` is the PR's head, empty for a PR this run opens. The template's reason is
    the run's own words: a head's text in it could fill a placeholder."""
    at_head = f" at PR head {short_sha(head)}" if head else ""
    reason = f"`review-work --force` passed each refusal below{at_head}."
    return "\n".join(
        [
            render_audit_comment(capability_root, invoker, reason),
            "",
            *(f"- {refusal}" for refusal in quoted),
            "",
            key,
        ]
    )


def _force_audited(
    pr_number: int | None,
    findings: list[pr_validation.Finding],
    head: str,
    capability_root: Path,
    invoker: Identity,
    config: dict,
    *,
    opened_url: str | None = None,
) -> bool:
    """Post the one audit comment of what `--force` passed of `findings`, and say
    whether the run may go on. True where the comment is on the PR, posted now or by
    an earlier try of the same override at the same head (`post_audit_once`), where
    `--force` passed nothing, and where `audit.projection` is `off`, which posts none
    (DEC-049 point 2). False, with why printed, where it cannot be posted. `opened_url`
    is a PR this run has just opened."""
    quoted = [_quoted(f) for f in findings if f.severity in OVERRIDDEN]
    if not quoted or audit_projection(config) == PROJECTION_OFF:
        return True
    # Hashed from the escaped words: raw, a lone surrogate in a description cannot encode.
    key = audit_key(FORCE_AUDIT_WRITER, head, *quoted)
    posted = post_audit_once(
        "pr",
        pr_number,
        key,
        _force_audit_body(quoted, head, key, capability_root, invoker),
        config,
        run=gh_run,
        present_note="--force audit comment already present; idempotent skip",
        posted_note="--force audit comment posted",
    )
    if not posted:
        print(_unaudited(pr_number, opened_url), file=sys.stderr)
    return posted


def _unaudited(pr_number: int | None, opened_url: str | None) -> str:
    """What a run says where the audit comment of its `--force` could not be posted.
    On a PR it opened, a second run is no way to the comment: only a PR going ready has
    its body validated, so that run finds nothing to override."""
    if opened_url is None:
        return (
            f"error: the audit comment of this --force could not be posted on PR #{pr_number}; "
            "nothing was made ready, no reviewer requested and the issue not moved. Run "
            "review-work --force again once it can be posted."
        )
    what, undo = _left_behind(
        pr_number=pr_number, opened_url=opened_url, flipped=False, reviewers=[]
    )[0]
    return (
        f"error: the audit comment of this --force could not be posted on {what}; no reviewer "
        "was requested and the issue not moved. A second run would not read those findings "
        f"again, since the PR is ready: undo it with `{undo}` and run again, or say on the PR "
        "what --force passed."
    )


#: What review-work reads of a PR: its description, the head and base the author's
#: sentences are checked against, and where that head is fetched from.
_DESCRIPTION_FIELDS = "body,headRefOid,baseRefName,headRefName,isCrossRepository"


def _gh_pr_description(pr_number: int | None, config: dict) -> _Description | None:
    """The current description of a PR, with its head and base: a draft's,
    validated before the flip → ready, or a ready one's, whose sentences are
    checked before the move. None, with what failed printed, when it cannot be
    read: a description unread is never read as one that gives every sentence."""
    if pr_number is None:
        print("error: cannot read the PR's description — no PR number resolved.", file=sys.stderr)
        return None
    try:
        proc = gh_run(
            ["gh", "pr", "view", str(pr_number), "--json", _DESCRIPTION_FIELDS],
            config,
            check=False,
        )
    except FileNotFoundError as exc:
        return _unread_body(pr_number, f"`gh` could not be run ({exc})")
    if proc.returncode != 0:
        return _unread_body(
            pr_number, (proc.stderr or "").strip() or f"gh exited {proc.returncode}"
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return _unread_body(pr_number, "gh's answer is not JSON")
    if not isinstance(data, dict):
        return _unread_body(pr_number, "gh's answer names no pull request")
    return _Description(
        str(data.get("body") or ""),
        number=pr_number,
        head=str(data.get("headRefOid") or ""),
        base=str(data.get("baseRefName") or ""),
        branch=str(data.get("headRefName") or ""),
        cross_repository=bool(data.get("isCrossRepository")),
    )


def _unread_body(pr_number: int, why: str) -> None:
    """Say that PR `pr_number`'s description could not be read, and why."""
    print(
        f"error: PR #{pr_number}'s description could not be read ({why}); nothing was made "
        "ready, no reviewer requested and the issue not moved. Run review-work again once it "
        "can be read.",
        file=sys.stderr,
    )


def _gh_pr_ready(pr_number: int | None, config: dict) -> bool:
    if pr_number is None:
        print("error: cannot flip PR to ready — no PR number resolved.", file=sys.stderr)
        return False
    proc = gh_run(
        ["gh", "pr", "ready", str(pr_number)],
        config,
        check=False,
    )
    if proc.returncode != 0:
        print(f"error: gh pr ready failed: {proc.stderr.strip()}", file=sys.stderr)
        return False
    return True


def _gh_pr_add_reviewers(pr_number: int, reviewers: list[str], config: dict) -> bool:
    cmd = ["gh", "pr", "edit", str(pr_number)]
    for r in reviewers:
        # Strip leading @ if present
        cmd += ["--add-reviewer", r.lstrip("@")]
    proc = gh_run(cmd, config, check=False)
    if proc.returncode != 0:
        print(
            f"error: gh pr edit --add-reviewer failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    path = capability_root / "project" / "members.yaml"
    if not path.is_file():
        return []
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []


def _read_classification(capability_root: Path, yaml_loader: YAML) -> dict:
    """The parsed classification.yaml, or {} when absent/unparseable.

    Feeds the branch-prefix cross-check's type-value → conv-type lookup
    (`pr_type_mapping`) and the title-prefix reverse read. A thin or missing
    schema degrades to {} — the prefix then resolves to None and the DEC-013
    branch cross-check is skipped rather than misfiring."""
    return _read_schema(capability_root, "classification.yaml", yaml_loader)


def _read_schema(capability_root: Path, name: str, yaml_loader: YAML) -> dict:
    """A parsed capability schema (`schemas/<name>`), or {} when absent or
    unparseable. A missing workflow.yaml therefore declares no legal moves and
    the transition gate refuses, as move-issue would."""
    path = capability_root / "schemas" / name
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    sys.exit(main())
