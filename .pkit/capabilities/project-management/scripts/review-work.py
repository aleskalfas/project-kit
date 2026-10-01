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

    review-work <N> [--reviewer @<user>] [--require-human]

Gates per DEC-026:
  - Membership (open-mode degrades to no-op).
  - Current branch matches `<type>/<N>-<slug>` AND `<type>` matches
    issue's `type:*` label per DEC-013.
  - Issue's current state can move to Review per workflow.yaml (or is
    already there, so a re-run works). Checked before any PR is opened or
    flipped ready and before reviewers are requested, so a refused move
    leaves the PR as it was (#947). From Backlog, move to In Progress first.
    The state is the one move-issue moves from, read once and handed to it
    (`_lib/issue_position`, #1242); a state that cannot be read refuses here
    too, saying why.
  - PR title is Conventional Commits.

Side-effects:
  - Opens a ready PR via `gh pr create` if none exists for the branch.
  - Flips an existing draft PR to ready via `gh pr ready` if present.
  - Reviewer assignment (v1 ships with simple --reviewer override path;
    full DEC-027 mode resolution lands in Phase D).
  - Composes over `move-issue.py --to review`. If that move still fails
    after the PR was opened or flipped ready (e.g. a network error), the run
    ends on a failure naming what it left behind: the PR, its ready state and
    the reviewers it requested.

Exit codes:
  0  PR ready + issue in Review (moved there, or already there)
  1  membership or foreign-repo refusal / PR body not ready for review
     (validate-at-ready; --force overrides)
  2  usage error / gate failure / illegal transition / unreadable state /
     issue not found
  3  gh failure: `gh pr create` could not open the PR, or `gh pr ready`
     could not make it ready
  *  a failed composed move-issue passes its exit code through
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
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
    issue_position,
    pr_validation,
    session_guard,
)
from _lib import lifecycle_inference as infer
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
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
            "findings (empty required section / checkbox / missing Doc impact). "
            "Drafts stay exempt; you normally fill a draft first (create-draft → "
            "edit-pr → review-work) or use open-pr --body-file."
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

    # Find local branch for issue + validate shape.
    branch = _find_issue_branch(args.issue_number)
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
    # requested, so a refusal changes nothing. The state is the one reading
    # move-issue moves from (#1242), as for start-work's gate (#942).
    position = issue_position.read(
        issue,
        issue_position.engine_status(args.issue_number),
        labels=labels,
        config=config,
        substrate_map=substrate_map,
    )
    refusal = composed_move.transition_refusal(
        "review-work",
        args.issue_number,
        issue,
        labels,
        position,
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
    existing_pr = _find_pr_for_branch(branch, config)
    pr_number: int | None = None
    # What this run changed on the PR, named if the composed move then fails.
    opened_url: str | None = None
    flipped = False
    if existing_pr is None:
        # Open a ready PR (non-draft) — validate the composed body first.
        title = _derive_pr_title(issue, branch)
        body = f"Closes #{args.issue_number}"
        if not _ready_body_ok(body, classification, capability_root, args.force):
            return 1
        url = _gh_pr_create_ready(branch, base, title, body, config)
        if url is None:
            return 3
        m = re.search(r"/pull/(\d+)", url)
        pr_number = int(m.group(1)) if m else None
        opened_url = url
        print(f"  opened ready PR: {url}")
    elif existing_pr.get("isDraft"):
        # Flip draft → ready — validate the draft's current body first.
        pr_number = existing_pr.get("number")
        if not _ready_body_ok(
            _gh_pr_body(pr_number, config), classification, capability_root, args.force
        ):
            return 1
        if not _gh_pr_ready(pr_number, config):
            return 3
        flipped = True
        print(f"  flipped PR #{pr_number} draft → ready")
    else:
        pr_number = existing_pr.get("number")
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
        position,
        capability_root_arg=args.capability_root,
        allow_foreign_repo=args.allow_foreign_repo,
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

    print(_success_line(args.issue_number, position.state, workflow))
    return 0


# ---- helpers -----------------------------------------------------------


def _find_issue_branch(issue_number: int) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "branch", "--list", "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    pattern = re.compile(rf"^[a-z]+/{issue_number}-[a-z0-9-]+$")
    for line in proc.stdout.splitlines():
        line = line.strip()
        if pattern.match(line):
            return line
    return None


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
    return gh_get_issue(issue_number, config, fields="title,labels,body,state,milestone")


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


def _success_line(issue_number: int, moved_from: str, workflow: dict) -> str:
    """The closing line of a run whose move-issue succeeded. A re-run from
    Review made no move, so it does not claim one."""
    name = infer.state_display_name
    if moved_from == TARGET_STATE:
        return f"\n[ok] PR ready; #{issue_number} already in {name(workflow, TARGET_STATE)}"
    return (
        f"\n[ok] PR ready + #{issue_number} "
        f"{name(workflow, moved_from)} → {name(workflow, TARGET_STATE)}"
    )


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


def _ready_body_ok(body: str, classification: dict, capability_root: Path, force: bool) -> bool:
    """Validate-at-ready (#569): True iff `body` may go ready-for-review.

    Runs the shared PR-body validator at the merge-gate phase (empty checkbox →
    hard-reject). Title/closing-label checks are skipped (review-work composes the
    title). On a blocking finding: print it and return False, or True under
    ``force``. Merge remains the backstop; drafts never reach here.
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
    blocking = [f for f in findings if f.severity in pr_validation.BLOCKING_SEVERITIES]
    if not blocking:
        return True
    print(
        "[refused] PR body is not ready for review (validate-at-ready, #569):",
        file=sys.stderr,
    )
    for f in blocking:
        print(f"  - [{f.severity}] {f.label}: {f.detail}", file=sys.stderr)
    if force:
        print("  → proceeding under --force.", file=sys.stderr)
        return True
    print(
        "  → fill the body first (create-draft → edit-pr → review-work), or use "
        "open-pr --body-file; --force overrides.",
        file=sys.stderr,
    )
    return False


def _gh_pr_body(pr_number: int | None, config: dict) -> str:
    """The current body of a PR (for validating a draft before flip → ready)."""
    if pr_number is None:
        return ""
    try:
        proc = gh_run(["gh", "pr", "view", str(pr_number), "--json", "body"], config, check=False)
    except FileNotFoundError:
        return ""
    if proc.returncode != 0:
        return ""
    try:
        return str((json.loads(proc.stdout) or {}).get("body") or "")
    except json.JSONDecodeError:
        return ""


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
