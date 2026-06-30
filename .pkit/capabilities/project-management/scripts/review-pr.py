#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — review-pr (DEC-028 + DEC-032 invocation).

Invokes every reviewer in the PR's *resolved required-local set* against the
PR's diff and posts each verdict as a comment under the developer's gh
identity. The verdict format is per DEC-028:

    Reviewer agent (local, <name>): APPROVED
    Reviewer agent (local, <name>): CHANGES_REQUESTED

followed by free-form commentary the agent produces.

    review-pr <N>

The required set is resolved per PR (DEC-032 D1) as the baseline
(`review.agents.local_registered:`) UNIONED with every contributed reviewer
whose match-predicate matches the classification of any issue the PR closes.
Crucially, this resolution is the SAME shared helper `done-work`'s gate
checks (`_lib.required_reviewers.resolve_required_local_reviewers`), so the
set `review-pr` invokes equals the set the gate later checks — the
developer-at-keyboard flow produces exactly the verdicts the gate needs, with
no divergence (DEC-032 D4).

Gates:
  - Membership (closed-mode refuses non-members).
  - PR must exist for the issue's branch.
  - The resolved required-local set must be non-empty.
  - Resolution must succeed: a not-ok contribution collection (malformed
    declaration / undeployed contributed agent) or an unresolvable
    closing-issue lookup surfaces as an error and aborts — a required
    reviewer is never silently skipped (fail-closed, DEC-032 D5),
    consistent with the gate's posture.

Side-effects:
  - For each locally-registered agent: invoke (via the harness's agent
    runtime), capture verdict + body, post as comment.
  - Idempotent at the PR level: post-dating-latest-commit handles
    staleness automatically per DEC-028. Re-running invokes the agent(s)
    again and posts fresh verdicts; prior verdicts remain in the
    comment history (the gate-checker selects latest-per-agent).

Agent invocation:
  At v1, the kit invokes Claude Code agents via the `claude` CLI when
  available. Adopters with non-Claude-Code harnesses or custom invocation
  flows can subclass / override by editing this script's `_invoke_agent`
  function. Per DEC-028, this capability ships a default `reviewer` agent
  at `.pkit/capabilities/project-management/agents/reviewer.md` that emits
  the local-path verdict format and applies pm conventions; adopters may
  configure `local_registered: name: reviewer` to use it, register their
  own agent under `.claude/agents/`, or replace the default entirely.

Exit codes:
  0  all required reviewers invoked + comments posted
  1  membership refusal
  2  usage error / no agents configured / gh failure / required set
     unresolvable (fail-closed)
  3  one or more agent invocations failed (verdicts not posted)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.closing_issue_fetchers import (  # noqa: E402
    issue_labels as _issue_labels_fetch,
    pr_closing_issue_numbers as _pr_closing_issue_numbers_fetch,
)
from _lib.required_reviewers import (  # noqa: E402
    ERROR_CLOSING_ISSUES,
    ERROR_COLLECTION,
    RequiredReviewersError,
    Resolution,
    resolve_required_local_reviewers,
)
from _lib.review_contributions import collect_contributions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Invoke every locally-registered review agent against the PR's "
            "diff; post each verdict as a comment. Per DEC-028."
        ),
    )
    parser.add_argument("issue_number", type=int)
    parser.add_argument(
        "--capability-root", type=Path, default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    parser.add_argument("--dry-run", action="store_true")
    session_guard.add_override_argument(parser)
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

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before posting any
    # review comment: target repo (cwd) vs session anchor (CLAUDE_PROJECT_DIR).
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    # Resolve registered local agents.
    local_agents = _get_local_registered(config)
    if not local_agents:
        print(
            "error: no agents configured in `review.agents.local_registered:`. "
            "Add an entry pointing at a deployed agent in .claude/agents/.",
            file=sys.stderr,
        )
        return 2

    # Find the issue's branch + PR.
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
    print(f"review-pr: #{args.issue_number}")
    print(f"  PR:     #{pr_number}")

    # Resolve repo-root for the agent invocation (walk up from capability_root).
    repo_root = capability_root.parent.parent.parent

    # DEC-032 D4: resolve the PR's required-local set — baseline ∪ contributed
    # reviewers matched against the closing issues' classification — via the
    # SAME shared helper `done-work`'s gate checks. Invoking exactly this set
    # is what makes invoke-set == gate-set (no divergence).
    baseline_local = [a["name"] for a in local_agents]
    resolution = _resolve_required_local(
        pr_number, config, repo_root, baseline_local
    )
    if not resolution.ok:
        # HARD ABORT on a non-ok resolution — and this is a DELIBERATE choice,
        # not a gate-safety requirement. review-pr is advisory: it posts
        # verdicts but does NOT gate the merge. done-work independently
        # re-resolves the required set at merge time and fails closed there
        # (DEC-032 D5) — that, not review-pr, is the real boundary. So aborting
        # here is NOT load-bearing for safety; even if review-pr invoked a
        # partial set or none at all, done-work would still refuse the merge.
        # We abort anyway for ONE consistent fail-closed posture across both
        # consumers and minimum surface: rather than invent a "warn and invoke
        # the baseline subset" middle path (a third behaviour to reason about
        # and test), review-pr simply produces no verdicts on a transient gh
        # blip. That is acceptable precisely because re-running review-pr is
        # cheap and done-work remains the gate. A future reader should treat
        # this as a chosen posture, not a correctness lever — do not "fix" it
        # to warn-and-continue (it wouldn't make merges any safer) nor lean on
        # it as if dropping it would open a gate hole (it wouldn't; done-work
        # closes that hole).
        print(_resolution_error_message(resolution), file=sys.stderr)
        return 2
    required_local = list(resolution.required_local)
    contributed_by = dict(resolution.contributed_by)
    print(f"  agents: {', '.join(required_local)}")

    # For each required reviewer, invoke and post verdict.
    failures = 0
    for name in required_local:
        agent_file = repo_root / ".claude" / "agents" / f"{name}.md"
        if not agent_file.is_file():
            provenance = (
                f" (required by capability `{contributed_by[name]}`)"
                if name in contributed_by else ""
            )
            print(
                f"  [{name}] error: agent file not found at {agent_file}"
                f"{provenance}",
                file=sys.stderr,
            )
            failures += 1
            continue

        if args.dry_run:
            print(f"  [{name}] (dry-run) would invoke against PR #{pr_number}")
            continue

        verdict, body = _invoke_agent(name, pr_number, config)
        if verdict is None:
            print(f"  [{name}] invocation failed; no verdict to post.", file=sys.stderr)
            failures += 1
            continue

        comment = _format_verdict_comment(name, verdict, body)
        if not _post_comment(pr_number, comment, config):
            print(f"  [{name}] could not post verdict comment.", file=sys.stderr)
            failures += 1
            continue

        print(f"  [{name}] posted {verdict}")

    if failures > 0:
        return 3
    return 0


# ---- agent invocation ------------------------------------------------


def _invoke_agent(
    name: str, pr_number: int | None, config: dict,
) -> tuple[str | None, str]:
    """Invoke a Claude Code agent against the PR diff.

    Returns (verdict, body) — verdict is "APPROVED" or "CHANGES_REQUESTED"
    or None on failure. Body is the agent's freeform commentary.

    At v1 this uses the `claude` CLI when available. Adopters with
    custom harnesses or invocation patterns override by editing this
    function. Per DEC-028's Implications, the methodology specifies
    the verdict-comment contract; the agent implementations are
    adopter / kit-side.
    """
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        print(
            "  [warn] `claude` CLI not on PATH. The kit's review-pr.py at v1 "
            "invokes Claude Code agents via the `claude` CLI; for adopters "
            "with other harnesses, edit `_invoke_agent` in review-pr.py to "
            "call your invocation flow.",
            file=sys.stderr,
        )
        return None, ""

    # Build the prompt — the agent receives the PR diff + a clear
    # instruction to return one of the two verdicts as the first line.
    prompt = (
        f"Review the diff of PR #{pr_number} in this repository. "
        f"Apply your usual review criteria. Output your verdict on the "
        f"VERY FIRST LINE in one of these exact forms:\n\n"
        f"  Reviewer agent (local, {name}): APPROVED\n"
        f"  Reviewer agent (local, {name}): CHANGES_REQUESTED\n\n"
        "Then add any commentary, findings, or rationale below."
    )

    try:
        proc = subprocess.run(
            [claude_bin, "-p", prompt, "--agent", name],
            capture_output=True, text=True, check=False, timeout=300,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"  [{name}] invocation error: {exc}", file=sys.stderr)
        return None, ""

    if proc.returncode != 0:
        print(
            f"  [{name}] agent exited {proc.returncode}: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None, ""

    # Scan the output for the DEC-028 local-path verdict line:
    #   Reviewer agent (local, <name>): APPROVED
    #   Reviewer agent (local, <name>): CHANGES_REQUESTED
    # LLM reviewer agents non-deterministically emit preamble before the
    # verdict, so we scan for the FIRST line (anywhere in the output) that
    # matches the grammar rather than requiring it on line 1 — a line-1-only
    # parse failed intermittently and posted no verdict, stalling the merge.
    # The match is exact (after stripping surrounding whitespace) and pinned
    # to THIS agent's name: review-pr only accepts a verdict from the agent it
    # actually invoked.
    #
    # Multi-match precedence: the FIRST matching line wins. A later,
    # possibly-contradictory verdict line in the same output is ignored — the
    # agent's verdict is taken to be the first one it commits to.
    #
    # Fail-closed: if NO line matches the grammar anywhere, return no verdict
    # so the caller posts nothing and the merge gate stays blocked.
    output = proc.stdout
    expected_approved = f"Reviewer agent (local, {name}): APPROVED"
    expected_changes = f"Reviewer agent (local, {name}): CHANGES_REQUESTED"
    lines = output.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == expected_approved:
            verdict = "APPROVED"
        elif stripped == expected_changes:
            verdict = "CHANGES_REQUESTED"
        else:
            continue
        # Body is the commentary following the verdict line; any preamble
        # before it is throat-clearing and dropped (the verdict line itself
        # is regenerated by `_format_verdict_comment`).
        body = "\n".join(lines[idx + 1:])
        return verdict, body

    # No grammar-matching line anywhere → fail-closed. Surface the agent's
    # FULL output (not a truncated first line) so the operator can debug the
    # non-conforming run.
    print(
        f"  [{name}] no DEC-028 verdict line found in agent output "
        f"(expected a line exactly {expected_approved!r} or "
        f"{expected_changes!r}). Full agent output follows:\n{output}",
        file=sys.stderr,
    )
    return None, ""


def _format_verdict_comment(name: str, verdict: str, body: str) -> str:
    """Compose the verdict comment in DEC-028's local-path format."""
    first_line = f"Reviewer agent (local, {name}): {verdict}"
    if body.strip():
        return f"{first_line}\n\n{body.strip()}"
    return first_line


# ---- required-set resolution (DEC-032 D1/D4) -------------------------


def _resolve_required_local(
    pr_number: int | None, config: dict, repo_root: Path, baseline_local: list[str],
) -> Resolution:
    """Resolve the PR's required-local set via the shared resolver (DEC-032 D1).

    Delegates to `_lib.required_reviewers.resolve_required_local_reviewers` —
    the SAME resolution `done-work`'s gate-checker calls — wiring in this
    script's own `gh`-backed closing-issue and label fetchers. Because both
    consumers go through one helper, the set this command invokes equals the
    set the gate later checks (DEC-032 D4, no divergence). Returns a
    `Resolution`; a non-ok result aborts (fail-closed, DEC-032 D5).

    A `None` `pr_number` (unresolvable PR) yields a non-ok resolution rather
    than a `gh` call against a missing number.
    """
    if pr_number is None:
        return Resolution(
            error=RequiredReviewersError(
                kind=ERROR_CLOSING_ISSUES,
                message="cannot resolve PR number",
            ),
        )
    return resolve_required_local_reviewers(
        pr_number,
        baseline_local=baseline_local,
        repo_root=repo_root,
        closing_issue_numbers=lambda n: _pr_closing_issue_numbers_fetch(
            n, config, gh_run=gh_run
        ),
        issue_labels=lambda n: _issue_labels_fetch(
            n, config, gh_get_issue=gh_get_issue
        ),
        collect_contributions=collect_contributions,
    )


def _resolution_error_message(resolution: Resolution) -> str:
    """Human error text for a non-ok `Resolution` that aborts review-pr.

    A not-ok contribution collection (malformed declaration / undeployed
    contributed agent) or an unresolvable closing-issue lookup aborts
    `review-pr` rather than invoke a partial set. The rationale for choosing a
    hard abort here — review-pr is advisory and done-work is the real gate, so
    this is a deliberate consistent-posture / minimum-surface choice, NOT a
    gate-safety requirement — is documented at the abort call site in `main()`.
    The text still frames the abort as fail-closed because that is what the
    operator sees and what keeps both consumers' messaging consistent.
    """
    error = resolution.error
    assert error is not None  # `not resolution.ok` guarantees this.
    lines = [
        "error: cannot resolve the required reviewer set for this PR — "
        "refusing to invoke a partial set (fail-closed, DEC-032 D5)."
    ]
    if error.kind == ERROR_COLLECTION and error.collection is not None:
        for err in error.collection.errors:
            where = (
                f"capability `{err.capability}`" if err.capability else "manifest"
            )
            lines.append(f"  → [{err.kind}] {where}: {err.message}")
        lines.append(
            "  Remediation: redeploy the contributing capability's agents, "
            "uninstall it, or fix the malformed contribution declaration."
        )
    else:
        lines.append(f"  → {error.message}")
        lines.append(
            "  Remediation: transient gh failure — retry; if persistent, "
            "check the PR's closing-issue links and labels."
        )
    return "\n".join(lines)


# ---- helpers ---------------------------------------------------------


def _get_local_registered(config: dict) -> list[dict]:
    review = config.get("review") if isinstance(config, dict) else None
    agents = review.get("agents") if isinstance(review, dict) else None
    if not isinstance(agents, dict):
        return []
    local = agents.get("local_registered") or []
    return [e for e in local if isinstance(e, dict) and e.get("name")]


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
         "--json", "number,isDraft,headRefName"],
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


def _post_comment(pr_number: int | None, body: str, config: dict) -> bool:
    if pr_number is None:
        return False
    proc = gh_run(
        ["gh", "pr", "comment", str(pr_number), "--body", body],
        config, check=False,
    )
    if proc.returncode != 0:
        print(f"error: gh pr comment failed: {proc.stderr.strip()}", file=sys.stderr)
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


if __name__ == "__main__":
    sys.exit(main())
