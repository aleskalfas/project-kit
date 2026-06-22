#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — done-work (DEC-026 workflow wrapper).

Transitions Review → Done by squash-merging the PR. Per DEC-026:

    done-work <N> [--bypass "<reason>"]

Approval gate (human-mode three-way OR per DEC-026):
  1. Latest review on the PR is APPROVED, OR
  2. The PR's last non-author comment starts with `Approved`, OR
  3. `--bypass "<reason>"` is supplied (writes an audit comment).

Phase D (DEC-027 mode resolution) wires the per-PR mode lookup that
chooses between this human-mode gate and DEC-028's agent-verdict gate.
v1 ships with the human-mode gate as the default.

Side-effects:
  - `gh pr merge --squash --delete-branch`.
  - `git pull` (main) after the merge.
  - Audit comment "Approved by bypass: <reason>" if --bypass is used
    (stamped + idempotent per DEC-024).
  - Composes over `move-issue.py --to done`.
  - `done-work` does NOT roll back the merge if a downstream step
    fails — merge irreversibility is the architectural constraint per
    DEC-026 failure semantics.

Exit codes:
  0  merged + done
  1  membership refusal / approval gate fails
  2  usage error / gh failure
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
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
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
from _lib.closing_issue_fetchers import (  # noqa: E402
    issue_labels as _issue_labels_fetch,
    pr_closing_issue_numbers as _pr_closing_issue_numbers_fetch,
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
    """Fetch issue labels for review-mode resolution (DEC-027)."""
    return gh_get_issue(issue_number, config, fields="labels")


BYPASS_AUDIT_STAMP = "<!-- pkit-hook: done-work-bypass -->"


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
            "Bypass the approval gate with a reason. Writes an audit "
            "comment 'Approved by bypass: <reason>' before merging."
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
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
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

    # Mode-conditional gate per DEC-026 + DEC-027 + DEC-028.
    if args.bypass:
        # --bypass overrides any mode; same audit-comment shape applies.
        gate_result = _GateResult(passed=True, passed_via=f"--bypass: {args.bypass}")
    elif mode_resolution.mode == "human":
        gate_result = _check_approval_gate(pr_number, pr, args.bypass, config)
    else:
        # agent mode — DEC-028 gate, with DEC-032's per-PR resolved set.
        gate_result = _check_agent_gate(
            pr_number, pr, config, mode_resolution.source, capability_root,
        )

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
    def __init__(self, passed: bool, passed_via: str = "", refusal_message: str = ""):
        self.passed = passed
        self.passed_via = passed_via
        self.refusal_message = refusal_message


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


# ---- agent-mode gate (DEC-028) ---------------------------------------


def _check_agent_gate(
    pr_number: int | None,
    pr: dict,
    config: dict,
    mode_source: str,
    capability_root: Path,
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
        return _resolution_refusal(resolution)
    required_local = list(resolution.required_local)
    # Provenance for the refusal message: reviewer name → contributing
    # capability (baseline reviewers have no contributing capability).
    contributed_by = dict(resolution.contributed_by)

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
    # TIMESTAMP (DEC-028 step 5), not by list order. A fresh
    # CHANGES_REQUESTED after a fresh APPROVED must correctly block, and vice
    # versa, regardless of how `gh` ordered the comments array. We track the
    # winning verdict's timestamp per agent and only let a later one override.
    # remote: github_login → (verdict, timestamp).
    remote_latest: dict[str, tuple[str, str]] = {}
    # local: agent name → (verdict, timestamp).
    local_latest: dict[str, tuple[str, str]] = {}

    def _record_latest(
        store: dict[str, tuple[str, str]], key: str, verdict: str, ts: str
    ) -> None:
        prior = store.get(key)
        # ISO-8601 (UTC `Z`) timestamps compare correctly as strings. Strict
        # `>` keeps the first-seen verdict on an exact tie (deterministic).
        if prior is None or ts > prior[1]:
            store[key] = (verdict, ts)

    for c in comments:
        if not isinstance(c, dict):
            continue
        comment_body = (c.get("body") or "")
        first_line = comment_body.split("\n", 1)[0].strip()
        comment_author = (c.get("author") or {}).get("login") or ""
        comment_ts = str(c.get("createdAt") or "")

        # Freshness: comment must post-date the latest commit.
        if comment_ts <= latest_commit_ts:
            continue

        # Remote path: identity match + author exclusion (DEC-028 step 2/3).
        if first_line in (
            "Reviewer agent: APPROVED", "Reviewer agent: CHANGES_REQUESTED"
        ):
            if comment_author in remote_baseline and comment_author != author_login:
                verdict = (
                    "APPROVED" if first_line.endswith("APPROVED")
                    else "CHANGES_REQUESTED"
                )
                _record_latest(remote_latest, comment_author, verdict, comment_ts)

        # Local path: name match in the body line; author-exclusion relaxed.
        local_verdict, local_who = _parse_local_verdict(first_line)
        if local_verdict is not None and local_who in required_local:
            _record_latest(local_latest, local_who, local_verdict, comment_ts)

    # Collapse to the latest verdict per agent (timestamp already selected).
    remote_status: dict[str, str] = {
        k: v[0] for k, v in remote_latest.items()
    }
    local_status: dict[str, str] = {
        k: v[0] for k, v in local_latest.items()
    }

    # --- DEC-032 D3 composition: per-reviewer OR-across-paths, AND-across-set.
    def reviewer_satisfied(name: str) -> bool:
        # A reviewer registered on both paths (a baseline name appearing in
        # both `remote_registered` and `local_registered`) is satisfied by
        # either path's fresh APPROVED — DEC-028's per-reviewer OR.
        if local_status.get(name) == "APPROVED":
            return True
        if name in remote_baseline and remote_status.get(name) == "APPROVED":
            return True
        return False

    # The required set spans the remote baseline plus the resolved local set.
    # A remote-only baseline reviewer is required on the remote path; a local
    # (baseline or contributed) reviewer on the local path.
    unsatisfied: list[str] = []
    for name in remote_baseline:
        if name not in required_local and remote_status.get(name) != "APPROVED":
            unsatisfied.append(name)
    for name in required_local:
        if not reviewer_satisfied(name):
            unsatisfied.append(name)

    if not unsatisfied:
        passed_via_parts: list[str] = []
        for name in remote_baseline:
            if name not in required_local:
                passed_via_parts.append(f"remote agent (@{name}) APPROVED")
        for name in required_local:
            label = _reviewer_label(name, contributed_by)
            passed_via_parts.append(f"{label} APPROVED")
        return _GateResult(
            passed=True,
            passed_via="; ".join(passed_via_parts),
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
        ),
    )


def _resolve_required_local(
    pr_number: int, config: dict, repo_root: Path, local_baseline: list[str],
) -> Resolution:
    """Resolve the PR's required-local set via the shared resolver (DEC-032 D1).

    Delegates to `_lib.required_reviewers.resolve_required_local_reviewers` —
    the SAME resolution `review-pr` calls — injecting the SHARED closing-issue
    and label fetchers (`_lib.closing_issue_fetchers`, the one definition both
    consumers import) wired to this script's `gh` helpers and
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
        collect_contributions=collect_contributions,
    )


def _resolution_refusal(resolution: Resolution) -> _GateResult:
    """Shape a fail-closed `_GateResult` from a non-ok `Resolution` (D5).

    A collection error names the malformed declaration / undeployed agent; an
    unresolvable closing-issue lookup names what could not be determined. Both
    refuse rather than proceed on a partial (fail-open) set.
    """
    error = resolution.error
    assert error is not None  # `not resolution.ok` guarantees this.
    if error.kind == ERROR_COLLECTION and error.collection is not None:
        return _GateResult(
            passed=False,
            refusal_message=_contribution_error_refusal(error.collection),
        )
    if error.kind == ERROR_CLOSING_ISSUES:
        return _GateResult(
            passed=False,
            refusal_message=_closing_issue_unresolvable_refusal(error.message),
        )
    # Defensive: any other (unexpected) kind still fails closed.
    return _GateResult(passed=False, refusal_message=error.message)


def _parse_local_verdict(first_line: str) -> tuple[str | None, str | None]:
    """Parse a local-path verdict line into (verdict, agent-name).

    Recognises DEC-028's local verdict shape
    `Reviewer agent (local, <name>): APPROVED|CHANGES_REQUESTED`. Returns
    `(None, None)` for any non-matching line. Generalises the old fixed-name
    match to any registered local name (the singleton cap lifts, DEC-032 D3).
    """
    match = _LOCAL_VERDICT_RE.match(first_line)
    if match is None:
        return None, None
    return match.group("verdict"), match.group("name")


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
) -> str:
    """Refusal text naming the full resolved required set + who lacks APPROVED.

    Names every required reviewer (baseline + contributed, with provenance)
    and its most recent fresh verdict, so the operator sees exactly which
    members of the AND-composed set still need to approve (DEC-032 D3).
    """
    lines = [
        "[refused] agent-mode approval required but the resolved reviewer set "
        "is not fully satisfied.",
        f"            → resolved mode: agent (source: {mode_source})",
        "            → required reviewers (all must have a fresh APPROVED):",
    ]
    for name in remote_baseline:
        if name not in required_local:
            status = remote_status.get(name) or "none"
            lines.append(f"                  remote @{name}: {status}")
    for name in required_local:
        label = _reviewer_label(name, contributed_by)
        # A reviewer on both paths shows the best of its two verdicts.
        status = local_status.get(name)
        if status != "APPROVED" and name in remote_baseline:
            status = remote_status.get(name) or status
        lines.append(f"                  {label}: {status or 'none'}")
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
    lines.append("              c) Merge with `done-work --bypass \"<reason>\"`.")
    lines.append(
        "              d) If no agent is configured, set `review.mode: human` "
        "or use --bypass."
    )
    return "\n".join(lines)


# DEC-028 local-path verdict line, generalised to any registered name.
_LOCAL_VERDICT_RE = re.compile(
    r"^Reviewer agent \(local, (?P<name>[^)]+)\): "
    r"(?P<verdict>APPROVED|CHANGES_REQUESTED)$"
)


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
