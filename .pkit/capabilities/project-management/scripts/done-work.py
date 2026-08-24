#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — done-work (DEC-026 workflow wrapper).

Transitions Review → Done by squash-merging the PR. Per DEC-026:

    done-work <N> [--bypass "<reason>"] [--bypass-ci "<reason>"]
                  [--skip-checkbox-gate]
                  [--bypass-reviewer <name> ... --bypass-reason "<r>"]

Approval gate (human-mode three-way OR per DEC-026):
  1. Latest review on the PR is APPROVED, OR
  2. The PR's last non-author comment starts with `Approved`, OR
  3. `--bypass "<reason>"` is supplied (writes an audit comment).

Checkbox close-gate (DEC-007, #734): a pre-flight in front of the merge —
every `- [ ]` in the closing issue's body must be ticked, else refuse,
listing each unticked line. It runs BEFORE the squash-merge is authorised
because GitHub's `Closes #N` auto-closes the issue *on* merge, so a check
afterwards would report a gate it had already let through. An issue with no
checkboxes at all is unaffected (the rule applies only when boxes exist); a
body that cannot be read fails closed. Overridable with
`--skip-checkbox-gate` (discouraged), mirroring `close-issue`'s flag. The
rule itself lives once in `_lib.checkbox_gate`, shared with `close-issue`,
`merge-pr` and the engine's `gate-checkboxes-ticked` predicate.

CI-status gate (#498): in front of the merge, the PR's `statusCheckRollup`
must be green — a failing or still-pending check refuses the merge (an
APPROVED verdict is not evidence CI passed). The general `--bypass` NEVER
clears a red or pending CI check; the CI gate is overridable only by the
dedicated `--bypass-ci "<reason>"`, which posts a distinct CI-bypass audit
comment to the PR before merging (bypassable-with-audit per
validation-severity.yaml). The two overrides are independent deliberate
acts: a merge blocked on both the approval gate and red CI needs both flags.

Per-reviewer override (DEC-050): in agent mode, `--bypass-reviewer <name>`
(repeatable, with a required `--bypass-reason`) satisfies ONE named required
reviewer's slot as `satisfied-by-override` — a first-class state DISTINCT from
a fresh APPROVED — while every other required reviewer still gates. It is a
member of DEC-046's `--bypass` family (audited, reason-required), NOT the
whole-gate `--bypass` (which discards the entire approval gate). The override
is ephemeral and merge-time: evaluated once against the currently-resolved set
and current HEAD, never persisted for a later run to read back. `satisfied-by-
override` is a separate gate-checker input, never a synthetic APPROVED verdict —
so it never corrupts the DEC-028 verdict record or the ADR-042 read surface. A
name not in the freshly-resolved required set is a hard error; overriding every
slot warns and points at `--bypass`. Before merging it posts a prose,
verdict-grammar-distinct audit comment per overridden reviewer (who/which/why +
the reviewer's state at override time), stamped per-reviewer(+reason) for
idempotency.

Phase D (DEC-027 mode resolution) wires the per-PR mode lookup that
chooses between this human-mode gate and DEC-028's agent-verdict gate.
v1 ships with the human-mode gate as the default.

Side-effects:
  - `gh pr merge --squash --delete-branch`.
  - `git pull` (main) after the merge.
  - Audit comment "Approved by bypass: <reason>" if --bypass is used
    (stamped + idempotent per DEC-024).
  - Per-reviewer-override audit comment(s) on the PR if --bypass-reviewer is
    used (prose, verdict-grammar-distinct, stamped per-reviewer(+reason) +
    idempotent per DEC-050).
  - Composes over `move-issue.py --to done`.
  - `done-work` does NOT roll back the merge if a downstream step
    fails — merge irreversibility is the architectural constraint per
    DEC-026 failure semantics.

Exit codes:
  0  merged + done
  1  membership refusal / approval, checkbox or CI gate fails
  2  usage error / gh failure
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.ci_checks import evaluate_ci_gate  # noqa: E402
# DEC-007's checkbox close-gate — the ONE implementation (`_lib.checkbox_gate`),
# shared with close-issue, merge-pr and the engine's gate-checkboxes-ticked
# predicate.
from _lib.checkbox_gate import (  # noqa: E402
    refusal_message as _checkbox_refusal,
    unticked_boxes,
)
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    Identity,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.placeholder_detection import (  # noqa: E402
    PHASE_TRANSITION,
    detect_placeholder_residuals,
)
from _lib.closing_issue_fetchers import (  # noqa: E402
    issue_labels as _issue_labels_fetch,
    pr_changed_files as _pr_changed_files_fetch,
    pr_closing_issue_numbers as _pr_closing_issue_numbers_fetch,
)
from _lib.agent_verdicts import (  # noqa: E402
    APPROVED,
    CHANGES_REQUESTED,
    PATH_LOCAL,
    PATH_REMOTE,
    gate_verdicts,
    latest_verdicts_per_reviewer,
)
from _lib.review_contributions import collect_contributions  # noqa: E402
from _lib.review_mode import resolve_mode  # noqa: E402
from _lib.required_reviewers import (  # noqa: E402
    ERROR_CLOSING_ISSUES,
    ERROR_COLLECTION,
    Resolution,
    resolve_required_local_reviewers,
)


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    """Fetch the issue's labels (review-mode resolution, DEC-027) and body (the
    DEC-007 checkbox pre-flight) in one round-trip."""
    return gh_get_issue(issue_number, config, fields="labels,body")


BYPASS_AUDIT_STAMP = "<!-- pkit-hook: done-work-bypass -->"
CI_BYPASS_AUDIT_STAMP = "<!-- pkit-hook: done-work-ci-bypass -->"
# Per-reviewer-override audit stamp (DEC-050). Distinct from the single
# whole-gate BYPASS_AUDIT_STAMP: keyed by reviewer name AND a short reason hash,
# so overriding a *different* reviewer — or the same reviewer with a *different*
# reason — posts its own audit, while re-running the identical override is a
# no-op. Built by `_reviewer_override_stamp`.
REVIEWER_OVERRIDE_STAMP_PREFIX = "<!-- pkit-hook: done-work-reviewer-override"


def _reviewer_override_stamp(reviewer: str, reason: str) -> str:
    """The per-reviewer(+reason) idempotency stamp for an override audit (DEC-050).

    Keyed by the reviewer name and a short hash of the (stripped) reason so the
    stamp is stable across re-runs with the same reviewer+reason (idempotent
    no-op) but differs when either changes (a fresh audit posts). The reason is
    hashed rather than inlined to keep the marker a single well-formed HTML
    comment regardless of the reason's characters.
    """
    reason_hash = hashlib.sha256(reason.strip().encode("utf-8")).hexdigest()[:12]
    return f"{REVIEWER_OVERRIDE_STAMP_PREFIX} name={reviewer} reason={reason_hash} -->"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Squash-merge the PR for an issue + transition Review → Done. "
            "Per DEC-026 with the human-mode three-way OR approval gate."
        ),
    )
    parser.add_argument("issue_number", type=int)
    parser.add_argument(
        "--bypass", default=None,
        help=(
            "Bypass the approval gate with a reason. Writes an audit comment "
            "'Approved by bypass: <reason>' on the issue before merging. Does "
            "NOT clear the CI-status gate (#498) — a red or pending CI still "
            "refuses; override CI separately with --bypass-ci."
        ),
    )
    parser.add_argument(
        "--bypass-ci", default=None,
        help=(
            "Override the CI-status gate (#498) with a reason "
            "(bypassable-with-audit per validation-severity.yaml). Records a "
            "distinct CI-bypass audit comment on the PR before merging. "
            "Independent of --bypass: a merge blocked on both the approval "
            "gate and red CI needs both flags."
        ),
    )
    parser.add_argument(
        "--skip-checkbox-gate", action="store_true",
        help=(
            "Skip the DEC-007 checkbox close-gate. Discouraged; only use "
            "when you have just removed all open boxes by hand."
        ),
    )
    parser.add_argument(
        "--bypass-reviewer", action="append", default=None, metavar="NAME",
        help=(
            "Satisfy ONE required reviewer's slot on the agent-mode approval "
            "gate by audited override, leaving every other required reviewer "
            "gating (DEC-050). Repeatable to override several named reviewers. "
            "Distinct from the whole-gate --bypass, which discards the entire "
            "approval gate: this waives one named reviewer and keeps the rest. "
            "Requires --bypass-reason. A name not in the freshly-resolved "
            "required set is a hard error. Overriding every slot warns and "
            "steers you to --bypass (the one honest whole-gate audit). Posts a "
            "verdict-distinct audit comment recording who/which/why + the "
            "reviewer's state at override time, before merging."
        ),
    )
    parser.add_argument(
        "--bypass-reason", default=None, metavar="REASON",
        help=(
            "The required reason paired with --bypass-reviewer (DEC-050). "
            "Applies to every reviewer named by --bypass-reviewer this "
            "invocation; recorded in each per-reviewer audit comment."
        ),
    )
    parser.add_argument(
        "--admin", action="store_true",
        help="Pass --admin to `gh pr merge` (bypass branch protection).",
    )
    parser.add_argument(
        "--capability-root", type=Path, default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("done-work", capability_root=capability_root):
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
    # merge / state transition: target repo (cwd) vs session anchor.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    branch = _find_issue_branch(args.issue_number)
    if branch is None:
        print(
            f"error: no local branch matching `*/{args.issue_number}-*` found.",
            file=sys.stderr,
        )
        return 2

    pr = _find_pr_for_branch(branch, config)
    if pr is None:
        print(
            f"error: no OPEN PR found for branch {branch!r}. "
            "Run `review-work` first.",
            file=sys.stderr,
        )
        return 2

    pr_number = pr.get("number")
    pr_title = pr.get("title") or ""
    if pr.get("isDraft"):
        print(
            f"error: PR #{pr_number} is still draft. Run `review-work` "
            "to flip it ready before `done-work`.",
            file=sys.stderr,
        )
        return 2

    # Resolve review mode per DEC-027 (issue labels read from the PR view above).
    issue = _gh_get_issue(args.issue_number, config)
    issue_labels = []
    if issue:
        issue_labels = [
            lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
            for lbl in (issue.get("labels") or [])
        ]
    mode_resolution = resolve_mode(config, issue_labels=issue_labels)
    print(f"  mode: {mode_resolution.mode} ({mode_resolution.source})")

    # Per-reviewer override (DEC-050) — a --bypass-family member. Reason is
    # required and paired via --bypass-reason (not inline). Validate the
    # pairing before any gate work.
    override_reviewers = tuple(args.bypass_reviewer or ())
    override_reason = (args.bypass_reason or "").strip()
    if override_reviewers and not override_reason:
        print(
            '[refused] --bypass-reviewer requires --bypass-reason "<reason>" '
            "(DEC-050: a per-reviewer override is audited, reason-required).",
            file=sys.stderr,
        )
        return 1
    if override_reason and not override_reviewers:
        print(
            "[warn] --bypass-reason was supplied without --bypass-reviewer; a "
            "reason applies only to a per-reviewer override, so it is ignored.",
            file=sys.stderr,
        )

    # Mode-conditional gate per DEC-026 + DEC-027 + DEC-028.
    if args.bypass:
        # --bypass overrides any mode; same audit-comment shape applies. A
        # whole-gate bypass discards the entire approval gate, so any
        # per-reviewer override flags are validated above (the reason-pairing
        # check runs before this branching, and so still refuses a
        # --bypass-reviewer with no --bypass-reason) but otherwise ignored here
        # — there is no per-reviewer slot left to satisfy.
        gate_result = _GateResult(passed=True, passed_via=f"--bypass: {args.bypass}")
    elif mode_resolution.mode == "human":
        # The per-reviewer override targets the agent-mode reviewer set; human
        # mode has no named required-reviewer set to override.
        if override_reviewers:
            print(
                "[refused] --bypass-reviewer applies to the agent-mode "
                "reviewer gate, but this PR resolved to human mode "
                f"(source: {mode_resolution.source}).\n"
                '          → Use --bypass "<reason>" for a whole-gate override '
                "in human mode, or set the PR to agent mode.",
                file=sys.stderr,
            )
            return 1
        gate_result = _check_approval_gate(pr_number, pr, args.bypass, config)
    else:
        # agent mode — DEC-028 gate, with DEC-032's per-PR resolved set and
        # DEC-050's satisfied-by-override OR-branch.
        gate_result = _check_agent_gate(
            pr_number, pr, config, mode_resolution.source, capability_root,
            override_reviewers=override_reviewers,
        )

    for warning in gate_result.warnings:
        print(warning, file=sys.stderr)

    if not gate_result.passed:
        print(gate_result.refusal_message, file=sys.stderr)
        return 1

    # Residual-placeholder check per DEC-031 — hard-reject at the merge gate.
    # Fetch the PR body (not fetched earlier; _find_pr_for_branch only
    # retrieves number/isDraft/headRefName).
    pr_body = _gh_get_pr_body(pr_number, config)
    if pr_body is not None:
        pr_placeholder_findings = _check_pr_placeholder(
            pr_body, pr_number, capability_root
        )
        hard_reject = [f for f in pr_placeholder_findings if f[0] == "hard-reject"]
        if hard_reject:
            print(
                f"[hard-reject] merge of PR #{pr_number} blocked: "
                "PR body has not been authored (DEC-031).",
                file=sys.stderr,
            )
            for sev, label, detail in hard_reject:
                print(f"  [{sev}] {label}: {detail}", file=sys.stderr)
            print(
                "  → Fill in the required sections of the PR body before merging.",
                file=sys.stderr,
            )
            return 1

    # Checkbox close-gate (DEC-007, #734) — the PR-merge closure path. Runs
    # BEFORE the merge is authorised: `Closes #N` auto-closes the issue *on*
    # merge, so a check afterwards gates nothing. Reads the body already
    # fetched above, so it costs no extra round-trip.
    checkbox_gate = _check_checkbox_gate(
        args.issue_number, issue, skip=args.skip_checkbox_gate
    )
    if not checkbox_gate.passed:
        print(checkbox_gate.refusal_message, file=sys.stderr)
        return 1
    # Report the outcome even when it passes: a gate nobody can see run is how
    # this one went missing for as long as it did (#734).
    print(f"  checkbox-gate: {checkbox_gate.passed_via}")

    # CI-status gate (#498). A satisfied approval gate is not evidence CI
    # passed — refuse to land a PR whose checks are red or still running. The
    # general `--bypass` (approval gate) does NOT clear this one: overriding a
    # flaky reviewer must never silently land a red CI (#498's whole point).
    # The CI gate is overridable only by the dedicated `--bypass-ci`, a
    # separate deliberate act, posting a distinct CI-bypass audit comment to
    # the PR before merging (bypassable-with-audit per validation-severity).
    rollup = _gh_get_status_rollup(pr_number, config)
    ci_gate = evaluate_ci_gate(rollup)
    if not ci_gate.passing:
        if not args.bypass_ci:
            print(
                f"[refused] CI-status gate for PR #{pr_number}: checks are "
                "not all green.\n"
                f"          failing/pending: {', '.join(ci_gate.failing_checks)}\n"
                "          → wait for the checks to pass, or override this CI "
                'gate explicitly with `--bypass-ci "<reason>"` (--bypass does '
                "not clear a red CI).",
                file=sys.stderr,
            )
            return 1
        if not args.bypass_ci.strip():
            print(
                "[refused] --bypass-ci requires a non-empty reason.",
                file=sys.stderr,
            )
            return 1
        print(
            "  ci-status: [bypass-ci] checks not green "
            f"({', '.join(ci_gate.failing_checks)}); reason: {args.bypass_ci.strip()}"
        )
    else:
        print("  ci-status: green")

    print(f"done-work: #{args.issue_number}")
    print(f"  PR:      #{pr_number}")
    print(f"  gate:    {gate_result.passed_via}")

    if args.dry_run:
        print(f"(dry-run: would post bypass audit (if any), squash-merge --subject {pr_title!r}, pull main, call move-issue.)")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Squash-merge + close? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # Post bypass audit comment if applicable.
    if args.bypass:
        if not _post_bypass_audit_idempotent(
            args.issue_number, args.bypass, config
        ):
            print(
                "[warn] could not post bypass audit comment; aborting before merge.",
                file=sys.stderr,
            )
            return 2

    # Post per-reviewer-override audit comment(s) before the merge (DEC-050).
    # Prose, verdict-grammar-distinct, stamped per-reviewer(+reason) so a
    # re-run of the same override is a no-op and a different reviewer/reason
    # posts anew. The trail lands before the merge so it survives a partial
    # failure (mirroring the CI-bypass audit).
    for audit in gate_result.override_audits:
        if not _post_reviewer_override_audit(
            pr_number, audit, override_reason, invoker, config
        ):
            print(
                "[warn] could not post reviewer-override audit comment; "
                "aborting before merge.",
                file=sys.stderr,
            )
            return 2

    # When --bypass-ci overrode a red/pending CI gate, record that explicitly
    # on the PR (bypassable-with-audit; the comment lands before the merge so
    # the trail survives a partial failure).
    if args.bypass_ci and not ci_gate.passing:
        if not _post_ci_bypass_audit(
            pr_number, args.bypass_ci.strip(), invoker, ci_gate.failing_checks, config
        ):
            print(
                "[warn] could not post CI-bypass audit comment; aborting "
                "before merge.",
                file=sys.stderr,
            )
            return 2

    # Squash-merge with an explicit subject so the landed commit subject
    # equals the gate-validated PR title regardless of commit count
    # (DEC-013: squash-commit subject = PR title; fixes #33).
    if not _gh_pr_merge(pr_number, pr_title=pr_title, admin=args.admin, config=config):
        return 3

    print(f"  merged PR #{pr_number}")

    # Pull main locally (best-effort; merge irreversibility means we don't
    # roll back on pull failure — the merge is durable).
    _git_pull_main()

    # Compose over move-issue for the state transition + cascade.
    rc = _invoke_move_issue(args.issue_number, "done", args.capability_root)
    if rc != 0:
        print(
            f"[warn] PR merged but move-issue exited {rc}. The merge is "
            "durable; re-run `move-issue --to done` to complete the "
            "lifecycle transition.",
            file=sys.stderr,
        )
        return rc

    print(f"\n[ok] merged + closed #{args.issue_number}")
    return 0


# ---- approval gate ---------------------------------------------------


class _GateResult:
    def __init__(
        self,
        passed: bool,
        passed_via: str = "",
        refusal_message: str = "",
        override_audits: "list[_OverrideAudit] | None" = None,
        warnings: "list[str] | None" = None,
    ):
        self.passed = passed
        self.passed_via = passed_via
        self.refusal_message = refusal_message
        # Per-reviewer-override audit records the caller posts before merging
        # (DEC-050) — empty unless the gate passed WITH one or more overrides.
        self.override_audits = override_audits or []
        # Soft, non-refusing notices the caller prints to stderr (e.g. the
        # all-slots override nudge, DEC-050).
        self.warnings = warnings or []


@dataclass(frozen=True)
class _OverrideAudit:
    """One overridden reviewer's audit record (DEC-050 Decision 4).

    Carries what the audit comment must record beyond the operator identity +
    reason (both supplied at post time): the overridden reviewer, its
    provenance (the contributing capability, or `None` for a baseline
    reviewer), a human-readable description of the reviewer's *state at
    override time* (`none` / a fresh `CHANGES_REQUESTED` / a stale `APPROVED`,
    per the DEC), and a link to the block comment when one exists.
    """

    reviewer: str
    capability: str | None
    state: str
    block_comment_url: str | None


def _check_approval_gate(
    pr_number: int | None, pr: dict, bypass_reason: str | None, config: dict
) -> _GateResult:
    """Human-mode three-way OR: APPROVED review OR `Approved`-prefix
    non-author comment OR --bypass."""
    if bypass_reason:
        if not bypass_reason.strip():
            return _GateResult(
                passed=False,
                refusal_message="error: --bypass requires a non-empty reason.",
            )
        return _GateResult(passed=True, passed_via=f"--bypass: {bypass_reason}")

    if pr_number is None:
        return _GateResult(
            passed=False, refusal_message="error: cannot resolve PR number.",
        )

    # Fetch the PR's reviews + comments + author.
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number),
         "--json", "author,reviews,comments"],
        config, check=False,
    )
    if proc.returncode != 0:
        return _GateResult(
            passed=False,
            refusal_message=(
                f"error: gh pr view failed: {proc.stderr.strip()}"
            ),
        )
    try:
        data = json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        return _GateResult(
            passed=False, refusal_message="error: gh pr view returned malformed JSON.",
        )
    author_login = (data.get("author") or {}).get("login") or ""

    # Path 1: latest APPROVED review (latest non-COMMENTED state).
    reviews = data.get("reviews") or []
    latest_states = [
        r.get("state") for r in reviews
        if isinstance(r, dict) and r.get("state") in (
            "APPROVED", "CHANGES_REQUESTED", "DISMISSED"
        )
    ]
    if latest_states and latest_states[-1] == "APPROVED":
        return _GateResult(passed=True, passed_via="APPROVED review")

    # Path 2: last non-author comment starts with `Approved` (case-sensitive).
    comments = data.get("comments") or []
    for c in reversed(comments):
        if not isinstance(c, dict):
            continue
        author = (c.get("author") or {}).get("login") or ""
        body = (c.get("body") or "").strip()
        if author and author != author_login and body.startswith("Approved"):
            return _GateResult(
                passed=True, passed_via=f"`Approved` comment from @{author}",
            )

    # Refused.
    return _GateResult(
        passed=False,
        refusal_message=(
            f"[refused] approval gate not satisfied for PR #{pr_number}.\n"
            "          → No APPROVED review present (latest state: "
            f"{latest_states[-1] if latest_states else 'none'}).\n"
            "          → No `Approved`-prefix comment from a non-author.\n"
            "          → No --bypass supplied.\n"
            "          Remediations:\n"
            "            - Request a review and have it approved.\n"
            "            - Have a non-author commenter post a comment "
            "starting with `Approved`.\n"
            "            - Re-run with `--bypass \"<reason>\"`."
        ),
    )


# ---- checkbox close-gate (DEC-007) -----------------------------------


def _check_checkbox_gate(
    issue_number: int, issue: dict | None, *, skip: bool
) -> _GateResult:
    """DEC-007's checkbox close-gate on the issue this merge closes.

    Markdown checkboxes are lifecycle-gating: an issue with an unticked box
    cannot reach Done. On the PR-merge path the check has to happen BEFORE the
    squash-merge is authorised — GitHub's `Closes #N` auto-closes the issue on
    merge, so a post-merge check could only report a gate it had already let
    through (DEC-007, "Task close via PR merge").

    An issue whose body carries no checkboxes at all passes: the rule applies
    only when boxes exist. A body that could NOT be read fails closed — an
    unverifiable gate is not a satisfied one, and the merge it guards is
    irreversible (the same posture as the agent gate's DEC-032 D5 refusals).

    Skippable with `--skip-checkbox-gate` (discouraged), mirroring
    `close-issue`'s flag of the same name and semantics.
    """
    if skip:
        return _GateResult(passed=True, passed_via="--skip-checkbox-gate")

    if issue is None:
        return _GateResult(
            passed=False,
            refusal_message=(
                f"[refused] DEC-007 checkbox close-gate for #{issue_number}: "
                "the issue body could not be read.\n"
                "          → `gh issue view` failed, so whether every checkbox "
                "is ticked is unknown; the gate refuses rather than merge on an "
                "unverified body (the merge auto-closes the issue and cannot be "
                "undone).\n"
                "          Remediation:\n"
                "            - Transient gh failure — retry `done-work`.\n"
                "            - If persistent, re-run with --skip-checkbox-gate "
                "(discouraged) after checking the boxes by hand."
            ),
        )

    unticked = unticked_boxes(str(issue.get("body") or ""))
    if not unticked:
        return _GateResult(passed=True, passed_via="all checkboxes ticked")

    return _GateResult(
        passed=False,
        refusal_message=_checkbox_refusal(
            unticked,
            scope=f"#{issue_number}, pre-merge",
            remedy=(
                "tick or remove each unticked checkbox before merging, or pass "
                "--skip-checkbox-gate (discouraged). The merge auto-closes the "
                "issue, so this cannot be fixed afterwards."
            ),
        ),
    )


# ---- agent-mode gate (DEC-028) ---------------------------------------


def _check_agent_gate(
    pr_number: int | None,
    pr: dict,
    config: dict,
    mode_source: str,
    capability_root: Path,
    *,
    override_reviewers: tuple[str, ...] = (),
) -> _GateResult:
    """DEC-028's gate-checker, generalised by DEC-032 to a per-PR resolved set.

    The resolved required local-reviewer set is the baseline
    (`review.agents.local_registered:`) UNIONED with every contributed
    reviewer whose match-predicate matches the classification of any issue
    the PR closes (DEC-032 D1), de-duplicated by reviewer name. The gate is
    satisfied iff *every* reviewer in the resolved set has a fresh APPROVED,
    each satisfiable via any path it is registered on (per-reviewer
    OR-across-paths, AND-across-the-set — DEC-032 D3, replacing DEC-028's
    steps 6–7; steps 1–5 below stand unchanged).

    Fail-closed (DEC-032 D5): if the contribution collection has any
    blocking error (a malformed declaration or a contributed reviewer whose
    agent is undeployed) the gate REFUSES rather than silently proceeding on
    the baseline — an unsatisfiable required reviewer cannot be dropped.

    For a project with only the static baseline and no contributions this is
    equivalent to the single-baseline case (DEC-032 D3: the per-reviewer-OR /
    across-set-AND rule coincides with DEC-028's cross-path OR when the
    resolved set has one reviewer).

    Per-reviewer override (DEC-050): `override_reviewers` names reviewers the
    operator waived this invocation with `--bypass-reviewer`. Each named
    reviewer's conjunct is ALSO satisfied by the override — a first-class
    `satisfied-by-override` state, a SEPARATE gate-checker input (never a
    synthetic APPROVED, so the DEC-028 verdict record / ADR-042 surface stay
    uncorrupted); AND-across-the-set is unchanged. Names are validated against
    the freshly-resolved required set (an unknown name is a hard error naming
    the set); overriding every slot warns and steers to `--bypass`. When the
    gate passes with one or more overrides, the result carries an
    `_OverrideAudit` per overridden reviewer (its state at override time) for
    the caller to post before merging. The override is ephemeral — evaluated
    once here against the current set + HEAD, never persisted.
    """
    review = config.get("review") if isinstance(config, dict) else None
    agents_block = review.get("agents") if isinstance(review, dict) else None
    if not isinstance(agents_block, dict):
        agents_block = {}
    remote_registered = agents_block.get("remote_registered") or []
    local_registered = agents_block.get("local_registered") or []

    if not remote_registered and not local_registered:
        return _GateResult(
            passed=False,
            refusal_message=(
                f"[refused] agent-mode approval gate cannot be satisfied — "
                f"no agents configured.\n"
                f"            → resolved mode: agent (source: {mode_source})\n"
                f"            → review.agents.remote_registered: (none)\n"
                f"            → review.agents.local_registered: (none)\n"
                "            Remediation:\n"
                "              a) Configure a registered agent in "
                "`project/config.yaml` under `review.agents.*`.\n"
                "              b) Set `review.mode: human` if you want "
                "human review instead.\n"
                "              c) Merge with `done-work --bypass \"<reason>\"`."
            ),
        )

    if pr_number is None:
        return _GateResult(
            passed=False, refusal_message="error: cannot resolve PR number.",
        )

    # Baseline required reviewer names per path (DEC-028's static lists).
    remote_baseline = [
        entry.get("github_login")
        for entry in remote_registered
        if isinstance(entry, dict) and entry.get("github_login")
    ]
    local_baseline = [
        entry.get("name")
        for entry in local_registered
        if isinstance(entry, dict) and entry.get("name")
    ]

    # --- DEC-032 D1: resolve the required-local set for this PR. -----------
    # Baseline ∪ contributed, de-duped, via the SHARED resolver `review-pr`
    # also calls — so the set this gate checks == the set `review-pr` invokes
    # (invoke-set == gate-set, the whole point of owning resolution once).
    # Recomputed at gate time (D5) from the current manifest + the PR's
    # current closing-issue classifications. Fail closed on any blocking
    # error (D5): a malformed declaration, an undeployed contributed agent,
    # or an unresolvable closing-issue lookup is never silently dropped.
    repo_root = capability_root.parent.parent.parent
    resolution = _resolve_required_local(
        pr_number, config, repo_root, local_baseline
    )
    if not resolution.ok:
        # An unresolvable set (broken contribution / undeployed agent) cannot
        # be helped by a per-reviewer override — the override operates WITHIN a
        # resolved set (DEC-050 Decision 5). Name that when overrides were
        # supplied so the operator reaches for the whole-gate --bypass instead.
        return _resolution_refusal(
            resolution, override_requested=bool(override_reviewers)
        )
    required_local = list(resolution.required_local)
    # Provenance for the refusal message: reviewer name → contributing
    # capability (baseline reviewers have no contributing capability).
    contributed_by = dict(resolution.contributed_by)

    # --- DEC-050: validate the per-reviewer override against the freshly-
    # resolved required set. A name not in the set is a HARD ERROR naming the
    # set (a typo, or a name dropped by reclassification/uninstall) — never a
    # silent no-op. The set spans the remote baseline plus the resolved local
    # set (a baseline reviewer may be remote).
    override_set = set(override_reviewers)
    required_set_all = set(remote_baseline) | set(required_local)
    unknown_overrides = [n for n in override_reviewers if n not in required_set_all]
    if unknown_overrides:
        return _GateResult(
            passed=False,
            refusal_message=_unknown_override_refusal(
                unknown_overrides, remote_baseline, required_local, contributed_by
            ),
        )

    # Soft all-slots nudge (DEC-050 Decision 6): overriding EVERY required slot
    # equals the whole-gate bypass by other means — allowed (it is audited),
    # but steer the operator to --bypass (one honest audit vs N per-reviewer
    # bypasses). A warning, not a refusal.
    gate_warnings: list[str] = []
    if override_set and override_set == required_set_all:
        gate_warnings.append(_all_slots_override_warning(required_set_all))

    # Fetch comments + author + the latest commit timestamp (one round-trip).
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number),
         "--json", "author,comments,commits"],
        config, check=False,
    )
    if proc.returncode != 0:
        return _GateResult(
            passed=False,
            refusal_message=f"error: gh pr view failed: {proc.stderr.strip()}",
        )
    try:
        data = json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        return _GateResult(
            passed=False, refusal_message="error: gh pr view returned malformed JSON.",
        )
    author_login = (data.get("author") or {}).get("login") or ""
    comments = data.get("comments") or []
    commits = data.get("commits") or []

    # Latest commit timestamp (DEC-028 step 4 freshness anchor). If it cannot
    # be established (no commits returned, or the last commit carries neither
    # committedDate nor authoredDate) the freshness boundary is UNKNOWN — so
    # the gate REFUSES rather than accept every stale verdict as fresh.
    # Fail-closed per DEC-032 D5; an unestablishable freshness anchor is not
    # "no freshness check".
    latest_commit_ts = ""
    if commits:
        last = commits[-1]
        if isinstance(last, dict):
            # gh pr view returns commits with committedDate field.
            latest_commit_ts = str(
                last.get("committedDate") or last.get("authoredDate") or ""
            )
    if not latest_commit_ts:
        return _GateResult(
            passed=False,
            refusal_message=_freshness_unresolvable_refusal(pr_number),
        )

    # --- Steps 1–5: latest fresh verdict per agent per path, selected by
    # TIMESTAMP (DEC-028 step 5), via the SHARED verdict selection
    # (`_lib.agent_verdicts`) that `show-pr --field review` also consumes — so
    # the two never diverge on which comment is a reviewer's current verdict
    # (COR-007). The gate goes through the strict `gate_verdicts` wrapper, whose
    # freshness + membership filters are REQUIRED args — the read-surface
    # primitive's permissive fail-open default is unreachable from here. The
    # gate scopes the selection to its concern by injecting:
    #   * freshness — `min_timestamp` drops comments not strictly after the
    #     latest commit (a fresh CHANGES_REQUESTED after a fresh APPROVED still
    #     blocks; the latest-by-timestamp rule handles the ordering);
    #   * membership — remote verdicts count only from a baseline login that is
    #     not the PR author (DEC-028 step 2/3); local verdicts only from a name
    #     in the resolved required set (DEC-032 D1).
    remote_baseline_set = set(remote_baseline)
    required_local_set = set(required_local)
    verdicts = gate_verdicts(
        comments,
        min_timestamp=latest_commit_ts,
        remote_reviewer_ok=lambda login: (
            login in remote_baseline_set and login != author_login
        ),
        local_reviewer_ok=lambda name: name in required_local_set,
    )
    remote_status: dict[str, str] = {
        v.reviewer: v.token for v in verdicts if v.path == PATH_REMOTE
    }
    local_status: dict[str, str] = {
        v.reviewer: v.token for v in verdicts if v.path == PATH_LOCAL
    }

    # --- DEC-032 D3 composition: per-reviewer OR-across-paths, AND-across-set;
    # DEC-050 adds the satisfied-by-override OR-branch.
    def reviewer_approved(name: str) -> bool:
        # A genuine fresh APPROVED on either path, independent of any override.
        # A reviewer registered on both paths (a baseline name appearing in
        # both `remote_registered` and `local_registered`) is satisfied by
        # either path's fresh APPROVED — DEC-028's per-reviewer OR.
        if local_status.get(name) == APPROVED:
            return True
        if name in remote_baseline and remote_status.get(name) == APPROVED:
            return True
        return False

    def reviewer_satisfied(name: str) -> bool:
        # DEC-050: an operator's audited override ALSO satisfies the conjunct —
        # a SEPARATE gate-checker input, never a synthetic APPROVED. A genuine
        # fresh APPROVED satisfies it too (and takes precedence in the honest
        # passed_via label below — a real approval is reported as such even
        # when the reviewer was also named in --bypass-reviewer).
        return reviewer_approved(name) or name in override_set

    # The required set spans the remote baseline plus the resolved local set.
    # A remote-only baseline reviewer is required on the remote path; a local
    # (baseline or contributed) reviewer on the local path.
    unsatisfied: list[str] = []
    for name in remote_baseline:
        if name not in required_local and not reviewer_satisfied(name):
            unsatisfied.append(name)
    for name in required_local:
        if not reviewer_satisfied(name):
            unsatisfied.append(name)

    if not unsatisfied:
        # Honest label: a genuine fresh APPROVED is reported as APPROVED even
        # when the reviewer was also named in --bypass-reviewer (the override
        # was redundant). Only a slot with no fresh APPROVED is labelled
        # satisfied-by-override (DEC-050 — the gate passes either way).
        passed_via_parts: list[str] = []
        for name in remote_baseline:
            if name not in required_local:
                if reviewer_approved(name):
                    passed_via_parts.append(f"remote agent (@{name}) APPROVED")
                else:
                    passed_via_parts.append(
                        f"remote agent (@{name}) satisfied-by-override"
                    )
        for name in required_local:
            label = _reviewer_label(name, contributed_by)
            if reviewer_approved(name):
                passed_via_parts.append(f"{label} APPROVED")
            else:
                passed_via_parts.append(f"{label} satisfied-by-override")
        # Build the per-reviewer audit records (state at override time) for the
        # caller to post before merging (DEC-050 Decision 4). Only when the
        # gate actually passes — a refused merge posts no audit.
        override_audits = _build_override_audits(
            override_reviewers=override_reviewers,
            comments=comments,
            latest_commit_ts=latest_commit_ts,
            contributed_by=contributed_by,
        )
        return _GateResult(
            passed=True,
            passed_via="; ".join(passed_via_parts),
            override_audits=override_audits,
            warnings=gate_warnings,
        )

    return _GateResult(
        passed=False,
        refusal_message=_agent_gate_refusal(
            mode_source=mode_source,
            remote_baseline=remote_baseline,
            required_local=required_local,
            contributed_by=contributed_by,
            remote_status=remote_status,
            local_status=local_status,
            unsatisfied=unsatisfied,
            override_set=override_set,
        ),
        warnings=gate_warnings,
    )


def _resolve_required_local(
    pr_number: int, config: dict, repo_root: Path, local_baseline: list[str],
) -> Resolution:
    """Resolve the PR's required-local set via the shared resolver (DEC-032 D1).

    Delegates to `_lib.required_reviewers.resolve_required_local_reviewers` —
    the SAME resolution `review-pr` calls — injecting the SHARED closing-issue,
    label, and changed-files fetchers (`_lib.closing_issue_fetchers`, the one
    definition both consumers import) wired to this script's `gh` helpers and
    `collect_contributions`. The fetcher lambdas reference `gh_run` /
    `gh_get_issue` as module globals, looked up at call time, so the agent-gate
    tests' monkeypatches of `collect_contributions` / `gh_run` / `gh_get_issue`
    on this module stay effective. Returns a `Resolution`; the caller maps a
    non-ok result to a `_GateResult` refusal (fail-closed, DEC-032 D5).
    """
    return resolve_required_local_reviewers(
        pr_number,
        baseline_local=local_baseline,
        repo_root=repo_root,
        closing_issue_numbers=lambda n: _pr_closing_issue_numbers_fetch(
            n, config, gh_run=gh_run
        ),
        issue_labels=lambda n: _issue_labels_fetch(
            n, config, gh_get_issue=gh_get_issue
        ),
        changed_files=lambda n: _pr_changed_files_fetch(
            n, config, gh_run=gh_run
        ),
        collect_contributions=collect_contributions,
    )


def _resolution_refusal(
    resolution: Resolution, *, override_requested: bool = False
) -> _GateResult:
    """Shape a fail-closed `_GateResult` from a non-ok `Resolution` (D5).

    A collection error names the malformed declaration / undeployed agent; an
    unresolvable closing-issue lookup names what could not be determined. Both
    refuse rather than proceed on a partial (fail-open) set.

    When `override_requested` (the operator passed `--bypass-reviewer`), append
    a note that a per-reviewer override cannot help an unresolvable set — it
    operates WITHIN a resolved set, so the whole-gate `--bypass` is the tool
    here (DEC-050 Decision 5).
    """
    error = resolution.error
    assert error is not None  # `not resolution.ok` guarantees this.
    if error.kind == ERROR_COLLECTION and error.collection is not None:
        message = _contribution_error_refusal(error.collection)
    elif error.kind == ERROR_CLOSING_ISSUES:
        message = _closing_issue_unresolvable_refusal(error.message)
    else:
        # Defensive: any other (unexpected) kind still fails closed.
        message = error.message
    if override_requested:
        message += (
            "\n            Note: --bypass-reviewer cannot help here — a "
            "per-reviewer override operates within a RESOLVED required set, "
            "and the set could not be resolved. Use the whole-gate "
            '--bypass "<reason>" (DEC-050).'
        )
    return _GateResult(passed=False, refusal_message=message)


def _reviewer_label(name: str, contributed_by: dict[str, str]) -> str:
    """Human label for a resolved local reviewer, with provenance.

    A contributed reviewer names the capability that required it; a baseline
    reviewer is unqualified.
    """
    capability = contributed_by.get(name)
    if capability:
        return f"local agent ({name}, required by capability `{capability}`)"
    return f"local agent ({name})"


def _contribution_error_refusal(collection) -> str:
    """Refusal text when contribution collection fails closed (DEC-032 D5)."""
    lines = [
        "[refused] agent-mode approval gate cannot be resolved — a reviewer "
        "contribution is unsatisfiable.",
    ]
    for err in collection.errors:
        where = f"capability `{err.capability}`" if err.capability else "manifest"
        lines.append(f"            → [{err.kind}] {where}: {err.message}")
    lines.append(
        "            The required-reviewer set cannot be resolved, so the "
        "gate refuses rather than merge on a partial set (fail-closed, "
        "DEC-032 D5)."
    )
    lines.append("            Remediation:")
    lines.append(
        "              a) Redeploy the contributing capability's agents "
        "(`pkit ... deploy-agents`), or"
    )
    lines.append(
        "              b) Uninstall the contributing capability if its gate "
        "is not wanted, or"
    )
    lines.append("              c) Fix the malformed contribution declaration, or")
    lines.append("              d) Merge with `done-work --bypass \"<reason>\"`.")
    return "\n".join(lines)


def _freshness_unresolvable_refusal(pr_number: int | None) -> str:
    """Refusal text when the latest-commit freshness anchor cannot be set.

    DEC-028 anchors verdict freshness to the latest commit's timestamp. If no
    commit timestamp can be established, every verdict's freshness is unknown
    — the gate refuses rather than accept a possibly-stale APPROVED as fresh
    (fail-closed, DEC-032 D5).
    """
    return "\n".join([
        f"[refused] agent-mode approval gate cannot be resolved for PR "
        f"#{pr_number} — the latest-commit freshness anchor is unknown.",
        "            → `gh pr view` returned no commit with a committedDate "
        "or authoredDate.",
        "            Verdict freshness is anchored to the latest commit "
        "(DEC-028); without it a stale APPROVED cannot be distinguished from "
        "a fresh one, so the gate refuses (fail-closed, DEC-032 D5).",
        "            Remediation:",
        "              a) Transient gh failure — retry `done-work`.",
        "              b) If persistent, merge with "
        "`done-work --bypass \"<reason>\"`.",
    ])


def _closing_issue_unresolvable_refusal(reason: str) -> str:
    """Refusal text when the PR's closing-issue classification is unknown.

    A transient gh failure resolving what the PR closes (or reading a closing
    issue's labels) leaves the contributed-reviewer set *unknown*. The gate
    refuses rather than proceed on the baseline alone (DEC-032 D5) — the same
    fail-closed posture the verdict-fetch uses on a gh failure.
    """
    return "\n".join([
        "[refused] agent-mode approval gate cannot be resolved — the PR's "
        "closing-issue classification is unknown.",
        f"            → {reason}",
        "            The contributed-reviewer set cannot be determined, so "
        "the gate refuses rather than merge on a possibly-incomplete set "
        "(fail-closed, DEC-032 D5).",
        "            Remediation:",
        "              a) Transient gh failure resolving closing issues — "
        "retry `done-work`.",
        "              b) If persistent, merge with "
        "`done-work --bypass \"<reason>\"`.",
    ])


def _agent_gate_refusal(
    *,
    mode_source: str,
    remote_baseline: list[str],
    required_local: list[str],
    contributed_by: dict[str, str],
    remote_status: dict[str, str],
    local_status: dict[str, str],
    unsatisfied: list[str],
    override_set: set[str] | None = None,
) -> str:
    """Refusal text naming the full resolved required set + who lacks APPROVED.

    Names every required reviewer (baseline + contributed, with provenance)
    and its most recent fresh verdict, so the operator sees exactly which
    members of the AND-composed set still need to approve (DEC-032 D3). A
    reviewer satisfied-by-override (DEC-050) shows that state rather than a
    verdict token — the gate still refuses because a DIFFERENT required
    reviewer is unsatisfied.
    """
    override_set = override_set or set()
    lines = [
        "[refused] agent-mode approval required but the resolved reviewer set "
        "is not fully satisfied.",
        f"            → resolved mode: agent (source: {mode_source})",
        "            → required reviewers (all must have a fresh APPROVED, or "
        "an operator override):",
    ]
    for name in remote_baseline:
        if name not in required_local:
            if name in override_set:
                status = "satisfied-by-override"
            else:
                status = remote_status.get(name) or "none"
            lines.append(f"                  remote @{name}: {status}")
    for name in required_local:
        label = _reviewer_label(name, contributed_by)
        if name in override_set:
            status = "satisfied-by-override"
        else:
            # A reviewer on both paths shows the best of its two verdicts.
            status = local_status.get(name)
            if status != "APPROVED" and name in remote_baseline:
                status = remote_status.get(name) or status
            status = status or "none"
        lines.append(f"                  {label}: {status}")
    missing = ", ".join(
        _reviewer_label(name, contributed_by) if name in required_local
        else f"remote @{name}"
        for name in unsatisfied
    )
    lines.append(f"            → still missing a fresh APPROVED: {missing}")
    lines.append("            Remediation:")
    lines.append(
        "              a) Wait for / trigger each remote agent to post APPROVED."
    )
    lines.append(
        "              b) Run `review-pr <N>` to re-invoke the local agent(s)."
    )
    lines.append(
        "              c) Override a false block on ONE reviewer with "
        '`done-work --bypass-reviewer <name> --bypass-reason "<r>"`.'
    )
    lines.append("              d) Merge with `done-work --bypass \"<reason>\"`.")
    lines.append(
        "              e) If no agent is configured, set `review.mode: human` "
        "or use --bypass."
    )
    return "\n".join(lines)


# ---- per-reviewer override (DEC-050) ---------------------------------


def _unknown_override_refusal(
    unknown: list[str],
    remote_baseline: list[str],
    required_local: list[str],
    contributed_by: dict[str, str],
) -> str:
    """Refusal text for a `--bypass-reviewer <name>` not in the resolved set.

    A hard error (DEC-050 Decision 5) — a typo, or a name dropped by
    reclassification/uninstall, must not silently no-op. Names the offending
    name(s) AND the full freshly-resolved required set so the operator sees
    exactly what is overridable this invocation.
    """
    resolved: list[str] = []
    for name in remote_baseline:
        if name not in required_local:
            resolved.append(f"remote @{name}")
    for name in required_local:
        resolved.append(_reviewer_label(name, contributed_by))
    return "\n".join([
        "[refused] --bypass-reviewer named a reviewer not in the freshly-"
        "resolved required set (DEC-050).",
        f"            → not required: {', '.join(unknown)}",
        f"            → resolved required set: {', '.join(resolved) or '(none)'}",
        "            A per-reviewer override must name a reviewer this PR "
        "actually requires — check for a typo, or a reviewer dropped by "
        "reclassification / a capability uninstall.",
        "            Remediation:",
        "              a) Re-run naming a reviewer from the resolved set above.",
        "              b) Merge with `done-work --bypass \"<reason>\"` for a "
        "whole-gate override.",
    ])


def _all_slots_override_warning(required_set_all: set[str]) -> str:
    """Warning text when `--bypass-reviewer` covers EVERY required slot (D6).

    Overriding every slot equals the whole-gate bypass by other means —
    allowed (it is audited), but N per-reviewer audits are noisier than one
    honest `--bypass`. A warning, not a refusal.
    """
    return (
        "[warn] --bypass-reviewer covers EVERY required reviewer "
        f"({', '.join(sorted(required_set_all))}) — this equals a whole-gate "
        'bypass. Consider `done-work --bypass "<reason>"` instead (one honest '
        "audit rather than N per-reviewer overrides). Proceeding (DEC-050)."
    )


def _build_override_audits(
    *,
    override_reviewers: tuple[str, ...],
    comments: list,
    latest_commit_ts: str,
    contributed_by: dict[str, str],
) -> "list[_OverrideAudit]":
    """One `_OverrideAudit` per overridden reviewer, with its state at override
    time (DEC-050 Decision 4).

    The state records why the reviewer's fresh-APPROVED slot was empty when
    overridden — the three states the DEC names (`none` / a fresh
    `CHANGES_REQUESTED` / a stale `APPROVED`), plus the remaining verdict/
    freshness combinations for completeness. It reads the reviewer's LATEST
    verdict regardless of freshness (via the shared `latest_verdicts_per_
    reviewer`, marker-required so only genuine reviewer verdicts count), so a
    stale APPROVED is distinguishable from an active block. The block comment's
    URL is carried when the latest verdict is a CHANGES_REQUESTED (a pointer to
    the block being waived).
    """
    override_names = set(override_reviewers)
    latest = latest_verdicts_per_reviewer(
        comments,
        remote_reviewer_ok=lambda login: login in override_names,
        local_reviewer_ok=lambda name: name in override_names,
        require_marker=True,
    )
    # When a name posted on both paths, keep the MOST-BLOCKING state so the
    # audit faithfully describes what was overridden — a fresh
    # CHANGES_REQUESTED (an active block) must win over a stale APPROVED rather
    # than the audit mis-recording "stale APPROVED" and dropping the block link
    # (DEC-050 audit fidelity). On a severity tie the first-seen verdict wins;
    # `latest` is sorted local-before-remote, preserving the prior local-first
    # tie-break.
    by_name: dict[str, "object"] = {}
    for verdict in latest:
        incumbent = by_name.get(verdict.reviewer)
        if incumbent is None or (
            _override_state_severity(verdict, latest_commit_ts)
            > _override_state_severity(incumbent, latest_commit_ts)
        ):
            by_name[verdict.reviewer] = verdict

    audits: list[_OverrideAudit] = []
    for name in override_reviewers:
        state, url = _describe_override_state(by_name.get(name), latest_commit_ts)
        audits.append(_OverrideAudit(
            reviewer=name,
            capability=contributed_by.get(name),
            state=state,
            block_comment_url=url,
        ))
    return audits


def _override_state_severity(verdict, latest_commit_ts: str) -> int:
    """Rank a reviewer's verdict by how much it necessitated the override.

    Used to pick the most faithful state to record when a reviewer posted on
    BOTH paths (DEC-050 audit fidelity): the audit should describe the
    most-blocking / least-satisfied state, not whichever path happened to sort
    first. Higher = more blocking:

        0  a fresh APPROVED           — satisfies the gate; override redundant
        1  a stale APPROVED           — predates HEAD, no longer counts
        2  a stale CHANGES_REQUESTED  — a recorded block, now stale
        3  a fresh CHANGES_REQUESTED  — an active block

    Freshness is relative to `latest_commit_ts` (strictly-after = fresh), the
    same anchor the gate and `_describe_override_state` use.
    """
    fresh = verdict.timestamp > latest_commit_ts
    if verdict.token == CHANGES_REQUESTED:
        return 3 if fresh else 2
    if verdict.token == APPROVED:
        return 0 if fresh else 1
    # Defensive: an unrecognised token ranks between APPROVED and
    # CHANGES_REQUESTED (fresh above stale) so it still wins over a satisfying
    # fresh APPROVED but yields to a real block.
    return 2 if fresh else 1


def _describe_override_state(
    verdict, latest_commit_ts: str
) -> "tuple[str, str | None]":
    """Human description + block-comment URL for a reviewer's state at override.

    Returns `(state, block_comment_url)`. `verdict` is the reviewer's latest
    marker-carrying verdict (a `Verdict`) or `None` when the reviewer never
    posted one. Freshness is relative to `latest_commit_ts` (strictly-after =
    fresh), the same anchor the gate uses.
    """
    if verdict is None:
        return "none (no verdict posted)", None
    fresh = verdict.timestamp > latest_commit_ts
    url = verdict.url or None
    if verdict.token == CHANGES_REQUESTED:
        if fresh:
            return "a fresh CHANGES_REQUESTED (an active block)", url
        return "a stale CHANGES_REQUESTED (predates the latest commit)", url
    if verdict.token == APPROVED:
        if fresh:
            # Overriding an already-fresh-APPROVED reviewer is redundant but
            # allowed — record it honestly rather than pretend it was blocked.
            return "a fresh APPROVED (override redundant)", None
        return "a stale APPROVED (predates the latest commit)", None
    # Defensive: an unrecognised token still audits.
    freshness = "fresh" if fresh else "stale"
    return f"a {freshness} {verdict.token}", url


# ---- side-effects ----------------------------------------------------


def _post_bypass_audit_idempotent(
    issue_number: int, reason: str, config: dict
) -> bool:
    body = f"{BYPASS_AUDIT_STAMP}\n\nApproved by bypass: {reason.strip()}"
    proc = gh_run(
        ["gh", "issue", "view", str(issue_number), "--json", "comments"],
        config, check=False,
    )
    if proc.returncode == 0:
        try:
            data = json.loads(proc.stdout)
            for c in data.get("comments", []):
                if BYPASS_AUDIT_STAMP in (c.get("body") or ""):
                    print("  bypass audit comment already present; idempotent skip")
                    return True
        except (ValueError, KeyError, TypeError):
            pass
    proc = gh_run(
        ["gh", "issue", "comment", str(issue_number), "--body", body],
        config, check=False,
    )
    if proc.returncode != 0:
        print(
            f"error: gh issue comment failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _gh_get_status_rollup(pr_number: int | None, config: dict) -> list[dict] | None:
    """Fetch the PR's `statusCheckRollup` for the CI-status gate (#498).

    Returns the rollup list on success, or None on failure — a None rollup is
    treated as an empty (check-free, passing) rollup by `evaluate_ci_gate`,
    matching the release-merge gate's empty-rollup semantics.
    """
    if pr_number is None:
        return None
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number), "--json", "statusCheckRollup"],
        config, check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        return None
    rollup = data.get("statusCheckRollup")
    return rollup if isinstance(rollup, list) else None


def _ci_bypass_audit_body(
    invoker: Identity, reason: str, failing_checks: tuple[str, ...]
) -> str:
    """Render the CI-bypass audit comment (validation-severity.yaml template).

    Follows the schema's `audit_comment_template`
    (`Bypassed by <name> <<email>>: <reason>`), naming the overridden checks
    and stamped for idempotency.
    """
    name = invoker.github_login or invoker.email or "<unresolved>"
    email = invoker.email or "<unknown>"
    checks = ", ".join(failing_checks) or "(none named)"
    return (
        f"{CI_BYPASS_AUDIT_STAMP}\n\n"
        f"Bypassed by {name} <{email}>: {reason}\n\n"
        f"CI-status gate overridden; non-passing checks: {checks}."
    )


def _post_ci_bypass_audit(
    pr_number: int | None,
    reason: str,
    invoker: Identity,
    failing_checks: tuple[str, ...],
    config: dict,
) -> bool:
    """Post the CI-bypass audit comment to the PR, idempotently."""
    if pr_number is None:
        return False
    body = _ci_bypass_audit_body(invoker, reason, failing_checks)
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number), "--json", "comments"],
        config, check=False,
    )
    if proc.returncode == 0:
        try:
            data = json.loads(proc.stdout)
            for c in data.get("comments", []):
                if CI_BYPASS_AUDIT_STAMP in (c.get("body") or ""):
                    print("  ci-bypass audit comment already present; idempotent skip")
                    return True
        except (ValueError, KeyError, TypeError):
            pass
    proc = gh_run(
        ["gh", "pr", "comment", str(pr_number), "--body", body],
        config, check=False,
    )
    if proc.returncode != 0:
        print(
            f"error: gh pr comment failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    print("  ci-bypass audit comment posted")
    return True


def _reviewer_override_audit_body(
    audit: "_OverrideAudit", reason: str, invoker: Identity
) -> str:
    """Render one per-reviewer-override audit comment (DEC-050 Decision 4).

    PROSE and verdict-grammar-distinct by construction: the first line is the
    idempotency stamp (an HTML comment), no line matches the DEC-028 verdict
    grammar (`Reviewer agent: ...` / `Reviewer agent (local, <name>): ...`),
    and the DEC-028 verdict marker (`<!-- pkit-verdict -->`) is never emitted —
    so neither the gate's verdict reader nor ADR-042's read surface counts it.
    Records the overridden reviewer + provenance, the operator (name + email),
    the reason, and the reviewer's state at override time with a link to the
    block comment when one exists.
    """
    name = invoker.github_login or invoker.email or "<unresolved>"
    email = invoker.email or "<unknown>"
    provenance = (
        f"required by capability `{audit.capability}`"
        if audit.capability else "baseline reviewer"
    )
    stamp = _reviewer_override_stamp(audit.reviewer, reason)
    lines = [
        stamp,
        "",
        f"Per-reviewer override by {name} <{email}>: {reason}",
        "",
        f"Overridden reviewer `{audit.reviewer}` ({provenance}).",
        f"Reviewer state at override time: {audit.state}.",
    ]
    if audit.block_comment_url:
        lines.append(f"Block comment: {audit.block_comment_url}")
    lines.append(
        "This reviewer's slot is satisfied-by-override for this merge; every "
        "other required reviewer still gated (project-management:DEC-050)."
    )
    return "\n".join(lines)


def _post_reviewer_override_audit(
    pr_number: int | None,
    audit: "_OverrideAudit",
    reason: str,
    invoker: Identity,
    config: dict,
) -> bool:
    """Post one per-reviewer-override audit comment to the PR, idempotently.

    Idempotency is keyed by the per-reviewer(+reason) stamp (DEC-050): a re-run
    of the identical override is a no-op, while overriding a DIFFERENT reviewer
    or the same reviewer with a DIFFERENT reason carries a distinct stamp and
    posts its own audit.
    """
    if pr_number is None:
        return False
    stamp = _reviewer_override_stamp(audit.reviewer, reason)
    body = _reviewer_override_audit_body(audit, reason, invoker)
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number), "--json", "comments"],
        config, check=False,
    )
    if proc.returncode == 0:
        try:
            data = json.loads(proc.stdout)
            for c in data.get("comments", []):
                if stamp in (c.get("body") or ""):
                    print(
                        f"  reviewer-override audit for `{audit.reviewer}` "
                        "already present; idempotent skip"
                    )
                    return True
        except (ValueError, KeyError, TypeError):
            pass
    proc = gh_run(
        ["gh", "pr", "comment", str(pr_number), "--body", body],
        config, check=False,
    )
    if proc.returncode != 0:
        print(
            f"error: gh pr comment failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    print(f"  reviewer-override audit posted for `{audit.reviewer}`")
    return True


def _gh_pr_merge(pr_number: int | None, *, pr_title: str, admin: bool, config: dict) -> bool:
    if pr_number is None:
        return False
    # Force --subject to the PR title so the squash-commit subject equals the
    # gate-validated title for both single- and multi-commit PRs.  GitHub's
    # default for a single-commit PR is the commit message, not the title —
    # the --subject flag overrides that (DEC-013; fixes #33).
    cmd = [
        "gh", "pr", "merge", str(pr_number),
        "--squash", "--delete-branch",
        "--subject", pr_title,
    ]
    if admin:
        cmd.append("--admin")
    proc = gh_run(cmd, config, check=False)
    if proc.returncode != 0:
        print(
            f"error: gh pr merge failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _git_pull_main() -> None:
    # Switch to main + pull. Best-effort; failures are warnings.
    proc = subprocess.run(
        ["git", "checkout", "main"], capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        print(
            f"[warn] git checkout main failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return
    proc = subprocess.run(
        ["git", "pull", "--ff-only"], capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        print(
            f"[warn] git pull failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )


# ---- PR-placeholder helpers ------------------------------------------

# Body-format descriptor for the PR placeholder check (mirrors the
# issue-side body-format.yaml structure).  ## Test plan is the only
# required checkbox section in PR.md.
_PR_BODY_FORMAT: dict = {
    "bodies": {
        "pr": {
            "required_sections": [
                {
                    "heading": "## Test plan",
                    "has_checkboxes": True,
                    "severity": "[validation-severity:hard-reject]",
                    "purpose": (
                        "Checkboxes describing the testing strategy. "
                        "Omit the section entirely for trivial changes; "
                        "when present, at least one authored item is required."
                    ),
                },
            ],
        },
    },
}


def _gh_get_pr_body(pr_number: int | None, config: dict) -> str | None:
    """Fetch the PR body via `gh pr view`.  Returns None on failure."""
    if pr_number is None:
        return None
    try:
        proc = gh_run(
            ["gh", "pr", "view", str(pr_number), "--json", "body"],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
        body = data.get("body")
        return str(body) if body is not None else ""
    except (json.JSONDecodeError, KeyError):
        return None


def _check_pr_placeholder(
    pr_body: str,
    pr_number: int | None,
    capability_root: "Path",
) -> list[tuple[str, str, str]]:
    """Run residual-placeholder detection on *pr_body* at PHASE_TRANSITION.

    Returns a list of ``(severity, label, detail)`` tuples — empty when clean.
    """
    return detect_placeholder_residuals(
        body=pr_body,
        structural_type="pr",
        body_format=_PR_BODY_FORMAT,
        capability_root=capability_root,
        phase=PHASE_TRANSITION,
    )


# ---- helpers -----------------------------------------------------------


def _find_issue_branch(issue_number: int) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "branch", "--list", "--format=%(refname:short)"],
            capture_output=True, text=True, check=False,
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


def _find_pr_for_branch(branch: str, config: dict) -> dict | None:
    proc = gh_run(
        ["gh", "pr", "list", "--head", branch, "--state", "open",
         "--json", "number,isDraft,headRefName,title"],
        config, check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        prs = json.loads(proc.stdout)
        for pr in prs:
            if pr.get("headRefName") == branch:
                return pr
    except (ValueError, KeyError):
        pass
    return None


def _invoke_move_issue(
    issue_number: int, target: str, capability_root_arg: Path | None
) -> int:
    cmd = [
        sys.executable, str(_HERE / "move-issue.py"),
        str(issue_number), "--to", target, "--yes",
    ]
    if capability_root_arg is not None:
        cmd += ["--capability-root", str(capability_root_arg)]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


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


if __name__ == "__main__":
    sys.exit(main())
