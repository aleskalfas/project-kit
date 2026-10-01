#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "pathspec>=0.12",
# ]
# ///
"""Project-management capability — review-pr (DEC-028 + DEC-032 invocation).

Invokes every reviewer in the PR's *resolved required-local set* against the
PR's diff and posts each verdict as a comment under the developer's gh
identity. The verdict format is per DEC-028:

    Reviewer agent (local, <name>): APPROVED
    Reviewer agent (local, <name>): CHANGES_REQUESTED

followed by free-form commentary the agent produces.

    review-pr <N> [--force]

The required set is resolved per PR (DEC-032 D1) as the baseline
(`review.agents.local_registered:`) UNIONED with every contributed reviewer
whose match-predicate matches the classification of any issue the PR closes,
less any contribution the project opts out of
(`review.agents.contributed_opt_out:`, #148 — listed in the output with its
reason). Crucially, this resolution is the SAME shared helper `done-work`'s gate
checks (`_lib.required_reviewers.resolve_required_local_reviewers`), so the
set `review-pr` invokes equals the set the gate later checks — the
developer-at-keyboard flow produces exactly the verdicts the gate needs, with
no divergence (DEC-032 D4).

Gates:
  - Membership (closed-mode refuses non-members).
  - PR must exist for the issue's branch.
  - The resolved required-local set must be non-empty.
  - Resolution must succeed: a not-ok contribution collection (malformed
    declaration / undeployed contributed agent), an invalid opt-out or
    not-code list, an unresolvable closing-issue lookup, or changed files
    that cannot be read surfaces as an error and aborts — a required reviewer
    is never silently skipped (fail-closed, DEC-032 D5), consistent with the
    gate's posture.

Side-effects:
  - For each required reviewer: read the PR's head commit, invoke the
    reviewer (via the harness's agent runtime) on that head, read the head
    again, and post the verdict as a comment whose marker names the head the
    reviewer was shown (`<!-- pkit-verdict sha=<oid> -->`, #1179). A head
    that moved during the review is reported and the verdict is still posted
    against the head it reviewed — the freshness rule then judges the
    changes since, exactly as for any later push; the native review is
    skipped, since GitHub would attach it to a head the reviewer never saw.
    When the head cannot be read the verdict names none and is judged by
    the latest commit's time.
  - Skips a required reviewer whose verdict is still fresh (#1178): its
    latest verdict is one the freshness rule (`_lib.verdict_freshness`, the
    one `done-work`'s gate applies, #1179) holds fresh, read with the SAME
    selection the gate counts (`gate_verdicts`), so a skipped reviewer is
    exactly one the gate would accept as it stands. It prints
    `[<name>] fresh verdict <APPROVED|CHANGES_REQUESTED> — not re-run`. A
    change the reviewer checks makes its verdict stale, so the next run
    invokes it; `--force` re-runs a fresh one (per DEC-046, the override of
    a stop the script makes). Prior verdicts remain in the comment history
    (the gate-checker selects latest-per-agent). When the PR's verdicts
    cannot be read, every required reviewer runs.

Agent invocation:
  At v1, the kit invokes Claude Code agents via the `claude` CLI when
  available. Adopters with non-Claude-Code harnesses or custom invocation
  flows can subclass / override by editing this script's `_invoke_agent`
  function. Per DEC-028, this capability ships a default `pm-reviewer` agent
  at `.pkit/capabilities/project-management/agents/pm-reviewer.md` that emits
  the local-path verdict format and applies pm conventions; adopters may
  configure `local_registered: name: pm-reviewer` to use it, register their
  own agent under `.claude/agents/`, or replace the default entirely.

Exit codes:
  0  every required reviewer invoked + comment posted, or skipped as fresh
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
from _lib import bootstrap_gate, session_guard
from _lib.agent_verdicts import PATH_LOCAL, gate_verdicts, stamp_verdict
from _lib.audit import short_sha
from _lib.author_delta import author_delta
from _lib.closing_issue_fetchers import issue_labels as _issue_labels_fetch
from _lib.closing_issue_fetchers import pr_changed_files as _pr_changed_files_fetch
from _lib.closing_issue_fetchers import pr_closing_issue_numbers as _pr_closing_issue_numbers_fetch
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.required_reviewers import (
    ERROR_CHANGED_FILES,
    ERROR_CLOSING_ISSUES,
    ERROR_COLLECTION,
    ERROR_NOT_CODE,
    ERROR_OPT_OUT,
    ERROR_TOO_MANY_CHANGED_FILES,
    NOT_CODE_PATH,
    RequiredReviewersError,
    Resolution,
    read_not_code,
    resolve_required_local_reviewers,
)
from _lib.review_contributions import collect_contributions
from _lib.review_opt_outs import OPT_OUT_PATH, read_opt_outs

# The one freshness rule (#1179), shared with done-work's gate and show-pr.
from _lib.verdict_freshness import PR_VIEW_FIELDS, FreshnessRule, rule_for_pr

# ---- per-agent reviewer timeout (issue #766) -------------------------
#
# The `claude` subprocess invoking each reviewer is capped by a wall-clock
# timeout. It is a SINGLE uniform knob applied to every reviewer — deliberately
# not a per-agent map (COR-007: one value, not a table to maintain). Reviewer
# agent runs are slow AND variable (observed 300s to >600s on the same
# reviewer), so the default is a GENEROUS CEILING — hit only on a genuinely
# hung agent, not a typical wait. It has been raised twice as the ceiling kept
# getting hit: 300s (original hardcode) → 600s → 1200s (300s killed heavier
# reviewers out of the box; 600s still timed out `code-reviewer` on a real
# panel review). Resolve once in `main()` and pass the value into every
# `_invoke_agent` call.
DEFAULT_AGENT_TIMEOUT = 1200
AGENT_TIMEOUT_ENV = "PKIT_REVIEW_AGENT_TIMEOUT"

# ---- per-agent reviewer effort (issue #1046) --------------------------
#
# A reviewer started headless reads the operator's user settings, so it
# reasons at whatever effort the operator set for their own interactive
# sessions. A review pass rarely needs that. Like the timeout, the effort is
# ONE uniform knob applied to every reviewer (COR-007: one value, not a
# per-agent map); the per-agent policy belongs to agent front matter (#1047).
# Precedence: `--effort` flag > `PKIT_REVIEW_AGENT_EFFORT` env var >
# `review.agents.effort` in the project config > unset, in which case no
# `--effort` is passed and the harness default applies. Resolve once in
# `main()` and pass the value into every `_invoke_agent` call.
AGENT_EFFORT_ENV = "PKIT_REVIEW_AGENT_EFFORT"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


def _resolve_agent_timeout(cli_value: str | None, env: dict) -> int:
    """Resolve the per-agent reviewer timeout in seconds.

    Precedence: `--timeout` flag > `PKIT_REVIEW_AGENT_TIMEOUT` env var >
    default (`DEFAULT_AGENT_TIMEOUT`). One uniform value applies to every
    reviewer (COR-007: no per-agent map).

    A non-integer, zero, or negative value is a usage error and raises
    `ValueError` with a helpful message (fail fast) rather than silently
    falling back to the default — a bad knob should be corrected, not ignored.
    """
    if cli_value is not None:
        raw: object = cli_value
        source = "--timeout"
    elif env.get(AGENT_TIMEOUT_ENV):
        raw = env[AGENT_TIMEOUT_ENV]
        source = f"${AGENT_TIMEOUT_ENV}"
    else:
        return DEFAULT_AGENT_TIMEOUT

    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(
            f"invalid reviewer timeout from {source}: {raw!r} is not an integer number of seconds."
        ) from None
    if value <= 0:
        raise ValueError(
            f"invalid reviewer timeout from {source}: {value} — must be a "
            "positive number of seconds."
        )
    return value


def _resolve_agent_effort(
    cli_value: str | None,
    env: dict,
    config: dict | None,
) -> tuple[str | None, str | None]:
    """Resolve the reviewer effort level and the source that set it.

    Returns `(level, source)`; `(None, None)` when nothing sets one.

    Precedence: `--effort` flag > `PKIT_REVIEW_AGENT_EFFORT` env var >
    `review.agents.effort` in the project config > None (the harness default
    applies; no `--effort` is passed). One uniform value applies to every
    reviewer (COR-007: no per-agent map).

    A value outside `EFFORT_LEVELS` is a usage error and raises `ValueError`
    naming its source (fail fast), never a silent fall-back. An empty flag,
    variable or config value is treated as absent.
    """
    review = config.get("review") if isinstance(config, dict) else None
    agents = review.get("agents") if isinstance(review, dict) else None
    configured = agents.get("effort") if isinstance(agents, dict) else None
    if cli_value:
        raw: object = cli_value
        source = "--effort"
    elif env.get(AGENT_EFFORT_ENV):
        raw = env[AGENT_EFFORT_ENV]
        source = f"${AGENT_EFFORT_ENV}"
    elif configured is not None and configured != "":
        raw = configured
        source = "review.agents.effort"
    else:
        return None, None
    if not isinstance(raw, str) or raw not in EFFORT_LEVELS:
        raise ValueError(
            f"invalid reviewer effort from {source}: {raw!r} — must be one of "
            + ", ".join(EFFORT_LEVELS)
            + "."
        )
    return raw, source


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Invoke every locally-registered review agent against the PR's "
            "diff; post each verdict as a comment. Per DEC-028."
        ),
    )
    parser.add_argument("issue_number", type=int)
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-native",
        action="store_true",
        help="Don't post a native GitHub review (APPROVE / REQUEST_CHANGES) — "
        "only the comment verdict. Per DEC-028 (amended). The native review is "
        "what shows in the PR UI and satisfies branch protection; it is skipped "
        "automatically when you authored the PR (GitHub blocks self-approval).",
    )
    parser.add_argument(
        "--timeout",
        default=None,
        metavar="SECONDS",
        help="Per-agent reviewer timeout in seconds (one uniform value applied "
        f"to every reviewer). Precedence: this flag > ${AGENT_TIMEOUT_ENV} env "
        f"var > default {DEFAULT_AGENT_TIMEOUT}. Must be a positive integer.",
    )
    parser.add_argument(
        "--effort",
        default=None,
        metavar="LEVEL",
        help="Effort level every reviewer reasons at (one uniform value). "
        f"Precedence: this flag > ${AGENT_EFFORT_ENV} env var > "
        "`review.agents.effort` in the project config > unset (the harness "
        "default). One of: " + ", ".join(EFFORT_LEVELS) + ".",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run every required reviewer, including one whose latest "
        "verdict is still fresh (skipped otherwise).",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    try:
        agent_timeout = _resolve_agent_timeout(args.timeout, os.environ)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("review-pr", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    try:
        agent_effort, effort_source = _resolve_agent_effort(
            args.effort,
            os.environ,
            config,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
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
            f"error: no OPEN PR found for branch {branch!r}. Run `review-work` first.",
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
    resolution = _resolve_required_local(pr_number, config, repo_root, baseline_local)
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
    for opt_out in resolution.opted_out:
        print(
            f"  opted out: {opt_out.reviewer} (capability "
            f"`{opt_out.capability}`) — {opt_out.reason}"
        )
    print(f"  timeout: {agent_timeout}s per agent")
    if agent_effort is None:
        print("  effort: harness default")
    else:
        print(f"  effort: {agent_effort} ({effort_source})")

    # A reviewer whose verdict is still fresh for this head is not re-run
    # (#1178) unless --force: re-running it reviews the same diff again.
    fresh: dict[str, str] = {}
    if not args.force:
        read = _read_fresh_verdicts(pr_number, resolution, config)
        if read is None:
            print("  fresh verdicts: could not be read — every required reviewer runs")
        else:
            fresh = read

    # For each required reviewer, invoke and post verdict.
    failures = 0
    for name in required_local:
        if name in fresh:
            print(f"  [{name}] fresh verdict {fresh[name]} — not re-run")
            continue

        agent_file = repo_root / ".claude" / "agents" / f"{name}.md"
        if not agent_file.is_file():
            provenance = (
                f" (required by capability `{contributed_by[name]}`)"
                if name in contributed_by
                else ""
            )
            print(
                f"  [{name}] error: agent file not found at {agent_file}{provenance}",
                file=sys.stderr,
            )
            failures += 1
            continue

        if args.dry_run:
            print(f"  [{name}] (dry-run) would invoke against PR #{pr_number}")
            continue

        # The head this reviewer is shown (#1179): read before the invocation,
        # named in its brief, and recorded in its verdict's marker.
        reviewed = _read_head_sha(pr_number, config)
        verdict, body = _invoke_agent(
            name,
            pr_number,
            config,
            agent_timeout,
            effort=agent_effort,
            base=pr.get("baseRefName"),
            head=branch,
            sha=reviewed,
        )
        if verdict is None:
            print(f"  [{name}] invocation failed; no verdict to post.", file=sys.stderr)
            failures += 1
            continue

        head_unchanged = _report_head_check(name, reviewed, _read_head_sha(pr_number, config))
        comment = _format_verdict_comment(name, verdict, body, sha=reviewed)
        if not _post_comment(pr_number, comment, config):
            print(f"  [{name}] could not post verdict comment.", file=sys.stderr)
            failures += 1
            continue

        print(f"  [{name}] posted {verdict}")

        # DEC-028 (amended): also deliver a NATIVE GitHub review carrying the
        # verdict state, so it shows in the PR UI and satisfies branch-protection
        # "required approving reviews". The comment above is what done-work's gate
        # reads; the native review is the GitHub-facing signal. Best-effort — a
        # failure or a self-approval degrade never fails review-pr (the comment
        # verdict stands). GitHub attaches a native review to the PR's current
        # head, so it is skipped when that is not the head the reviewer saw.
        if not args.no_native:
            if head_unchanged:
                _deliver_native_review(pr_number, verdict, comment, config)
            else:
                print(
                    "  [native] skipped — the PR's head is not the one the "
                    "reviewer saw. The comment verdict stands."
                )

    if fresh:
        print("  --force re-runs a reviewer whose verdict is fresh.")
    if failures > 0:
        return 3
    return 0


# ---- agent invocation ------------------------------------------------


def _invoke_agent(
    name: str,
    pr_number: int | None,
    config: dict,
    timeout: int = DEFAULT_AGENT_TIMEOUT,
    effort: str | None = None,
    *,
    base: str | None = None,
    head: str = "HEAD",
    sha: str = "",
) -> tuple[str | None, str]:
    """Invoke a Claude Code agent against the PR diff.

    Returns (verdict, body) — verdict is "APPROVED" or "CHANGES_REQUESTED"
    or None on failure. Body is the agent's freeform commentary.

    `timeout` is the per-agent wall-clock cap in seconds (issue #766); a
    reviewer that runs longer is killed and yields no verdict. The caller
    resolves the value once (`_resolve_agent_timeout`) and passes the same
    uniform value for every reviewer.

    `effort` is the effort level the reviewer reasons at (issue #1046),
    passed to the harness as `--effort`; None passes nothing and the harness
    default applies. Resolved once by the caller (`_resolve_agent_effort`),
    the same uniform value for every reviewer.

    `base` and `head` are the PR's base branch and its branch, named in the
    brief's local-diff fallback (see `_review_brief`); `sha` is the PR head
    commit the reviewer is to review, "" when it could not be read.

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

    prompt = _review_brief(name, pr_number, base=base, head=head, sha=sha)

    try:
        command = [claude_bin, "-p", prompt, "--agent", name]
        if effort is not None:
            command += ["--effort", effort]
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
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
        body = "\n".join(lines[idx + 1 :])
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


def _review_brief(
    name: str,
    pr_number: int | None,
    *,
    base: str | None,
    head: str,
    sha: str = "",
) -> str:
    """The prompt each reviewer receives: the PR, the head under review, a
    fallback for its diff, the verdict grammar.

    The brief names the head commit the reviewer is reviewing (#1179) — the
    one its verdict will be recorded against — so the reviewer can tell when
    the PR moved under it. GitHub refuses `gh pr diff` for a PR changing more
    than 300 files, so the brief also names the same diff in this checkout:
    the three-dot range from the PR's base branch to that head (to its branch
    when the head could not be read), which diffs from their merge base. An
    unknown base is left as a placeholder the reviewer fills from the PR's
    `baseRefName`.
    """
    reviewing = (
        f"You are reviewing its head commit {sha}; your verdict is recorded against that commit. "
        if sha
        else ""
    )
    return (
        f"Review the diff of PR #{pr_number} in this repository. "
        f"{reviewing}"
        f"If `gh pr diff {pr_number}` refuses it as too large (GitHub stops at "
        "300 changed files), read it from this checkout instead: "
        f"`git diff origin/{base or '<base>'}...{sha or head}`. "
        f"Apply your usual review criteria. Output your verdict on the "
        f"VERY FIRST LINE in one of these exact forms:\n\n"
        f"  Reviewer agent (local, {name}): APPROVED\n"
        f"  Reviewer agent (local, {name}): CHANGES_REQUESTED\n\n"
        "Then add any commentary, findings, or rationale below."
    )


def _format_verdict_comment(name: str, verdict: str, body: str, *, sha: str = "") -> str:
    """Compose the verdict comment in DEC-028's local-path format, stamped with
    the verdict marker (#593) so the merge gate counts it — naming `sha`, the
    head the reviewer was shown, when it is known (#1179)."""
    first_line = f"Reviewer agent (local, {name}): {verdict}"
    composed = f"{first_line}\n\n{body.strip()}" if body.strip() else first_line
    return stamp_verdict(composed, sha)


def _read_head_sha(pr_number: int | None, config: dict) -> str:
    """The PR's head commit as GitHub reports it, or "" when it cannot be read."""
    if pr_number is None:
        return ""
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number), "--json", "headRefOid"],
        config,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return ""
    return str(data.get("headRefOid") or "") if isinstance(data, dict) else ""


def _report_head_check(name: str, reviewed: str, now: str) -> bool:
    """Whether the PR's head is still the one `name` reviewed; says so when not.

    A verdict is posted against the head it reviewed either way (#1179) — the
    freshness rule judges what changed since. When the head was never read the
    verdict names none, is judged by the latest commit's time, and nothing is
    claimed about a head, so the check passes.
    """
    if not reviewed:
        print(
            f"  [{name}] the PR's head could not be read — the verdict names no "
            "reviewed head and is judged by the latest commit's time."
        )
        return True
    if now == reviewed:
        return True
    if now:
        moved = f"moved from {short_sha(reviewed)} to {short_sha(now)} during the review"
    else:
        moved = f"could not be read again after the review of {short_sha(reviewed)}"
    print(
        f"  [{name}] the PR's head {moved} — the verdict is recorded against "
        f"{short_sha(reviewed)}, and the changes since decide whether it stands."
    )
    return False


# ---- native GitHub review delivery (DEC-028, amended) ----------------


def _deliver_native_review(
    pr_number: int,
    verdict: str,
    body: str,
    config: dict,
) -> None:
    """Post a native `gh pr review` carrying the verdict state (DEC-028, amended).

    APPROVED → `--approve`, CHANGES_REQUESTED → `--request-changes`. The verdict
    comment (already posted) carries the pkit gate marker; this native review is
    the GitHub-facing state (PR UI + branch protection). Best-effort:

    - **Self-approval degrade.** GitHub refuses to approve *or* request changes on
      your own PR, so when the reviewer identity == the PR author, the native
      review is skipped (the comment verdict stands). Native delivery is fully
      autonomous only on a non-author / bot identity.
    - **Failure degrade.** Any gh failure (permission, API) is reported and skipped
      — never fails review-pr.
    """
    author = _gh_pr_author(pr_number, config)
    me = _gh_current_login(config)
    if author and me and author == me:
        print(
            f"  [native] skipped — you authored PR #{pr_number}; GitHub blocks a "
            "native review of your own PR. The comment verdict stands."
        )
        return
    event = "--approve" if verdict == "APPROVED" else "--request-changes"
    proc = gh_run(
        ["gh", "pr", "review", str(pr_number), event, "--body", body],
        config,
        check=False,
    )
    if proc.returncode != 0:
        print(
            f"  [native] could not post native review ({proc.stderr.strip()}); "
            "the comment verdict stands.",
            file=sys.stderr,
        )
        return
    state = "APPROVE" if verdict == "APPROVED" else "REQUEST_CHANGES"
    print(f"  [native] posted native GitHub review ({state}).")


def _gh_pr_author(pr_number: int, config: dict) -> str | None:
    """The PR author's login, or None if it can't be determined."""
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number), "--json", "author"],
        config,
        check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        return (json.loads(proc.stdout).get("author") or {}).get("login") or None
    except (ValueError, KeyError):
        return None


def _gh_current_login(config: dict) -> str | None:
    """The authenticated gh user's login, or None if it can't be determined."""
    proc = gh_run(["gh", "api", "user", "--jq", ".login"], config, check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


# ---- required-set resolution (DEC-032 D1/D4) -------------------------


def _resolve_required_local(
    pr_number: int | None,
    config: dict,
    repo_root: Path,
    baseline_local: list[str],
) -> Resolution:
    """Resolve the PR's required-local set via the shared resolver (DEC-032 D1).

    Delegates to `_lib.required_reviewers.resolve_required_local_reviewers` —
    the SAME resolution `done-work`'s gate-checker calls — wiring in this
    script's own `gh`-backed closing-issue, label, and changed-files fetchers
    and the project's contribution opt-outs (#148) and not-code list (#1178),
    read from `config` the same way the gate reads them. Because both
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
        closing_issue_numbers=lambda n: _pr_closing_issue_numbers_fetch(n, config, gh_run=gh_run),
        issue_labels=lambda n: _issue_labels_fetch(n, config, gh_get_issue=gh_get_issue),
        changed_files=lambda n: _pr_changed_files_fetch(n, config, gh_run=gh_run),
        opt_outs=read_opt_outs(config),
        not_code=read_not_code(config),
        collect_contributions=collect_contributions,
    )


# ---- fresh-verdict skip (#1178) --------------------------------------


def _read_fresh_verdicts(
    pr_number: int | None,
    resolution: Resolution,
    config: dict,
) -> dict[str, str] | None:
    """The required reviewers whose latest verdict on the PR is still fresh.

    Fetches the PR's comments, commits, head and base in one round-trip (the
    fetch `done-work`'s gate makes), builds the freshness rule from them and
    the PR's resolution (`rule_for_pr`, the gate's own), and hands both to
    `_fresh_local_verdicts`. Returns None when they cannot be read — the
    caller then runs every required reviewer, the direction that can only
    produce more verdicts.
    """
    if pr_number is None:
        return None
    proc = gh_run(
        ["gh", "pr", "view", str(pr_number), "--json", ",".join(("comments", *PR_VIEW_FIELDS))],
        config,
        check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return _fresh_local_verdicts(
        data.get("comments") or [],
        rule_for_pr(data, resolution, author_delta=author_delta),
        resolution.required_local,
    )


def _fresh_local_verdicts(
    comments: list,
    freshness: FreshnessRule,
    required_local: tuple[str, ...] | list[str],
) -> dict[str, str]:
    """Reviewer name → verdict token, for each required reviewer whose latest
    verdict is still fresh.

    The selection is `done-work`'s own: `gate_verdicts` (marker required,
    latest verdict per reviewer by timestamp, counted only when fresh) with the
    gate's freshness rule, scoped to the required local set. So a reviewer this skips is one the
    gate would count as it stands — a fresh APPROVED satisfies it, a fresh
    CHANGES_REQUESTED blocks it until a change its reviewer checks. Only
    local-path verdicts are read: `review-pr` invokes local reviewers, and a
    remote verdict is not one of theirs.
    """
    required = set(required_local)
    verdicts = gate_verdicts(
        comments,
        is_fresh=freshness.is_fresh,
        local_reviewer_ok=lambda name: name in required,
        remote_reviewer_ok=lambda _login: False,
    )
    return {v.reviewer: v.token for v in verdicts if v.path == PATH_LOCAL}


def _resolution_error_message(resolution: Resolution) -> str:
    """Human error text for a non-ok `Resolution` that aborts review-pr.

    A not-ok contribution collection (malformed declaration / undeployed
    contributed agent), an unresolvable closing-issue lookup, or changed files
    that cannot be read aborts `review-pr` rather than invoke a partial set,
    and each kind names its own remediation — a retry only where one can help.
    The rationale for choosing a hard abort here — review-pr is advisory and
    done-work is the real gate, so this is a deliberate consistent-posture /
    minimum-surface choice, NOT a gate-safety requirement — is documented at
    the abort call site in `main()`. The text still frames the abort as
    fail-closed because that is what the operator sees and what keeps both
    consumers' messaging consistent.
    """
    error = resolution.error
    assert error is not None  # `not resolution.ok` guarantees this.
    lines = [
        "error: cannot resolve the required reviewer set for this PR — "
        "refusing to invoke a partial set (fail-closed, DEC-032 D5)."
    ]
    if error.kind == ERROR_COLLECTION and error.collection is not None:
        for err in error.collection.errors:
            where = f"capability `{err.capability}`" if err.capability else "manifest"
            lines.append(f"  → [{err.kind}] {where}: {err.message}")
        lines.append(
            "  Remediation: redeploy the contributing capability's agents, "
            "uninstall it, or fix the malformed contribution declaration."
        )
    elif error.kind == ERROR_OPT_OUT:
        for detail in error.details:
            lines.append(f"  → {detail}")
        lines.append(
            f"  Remediation: fix or remove the entry in `{OPT_OUT_PATH}` "
            "(project/config.yaml) — each names an installed capability, a "
            "reviewer it contributes, and a reason."
        )
    elif error.kind == ERROR_NOT_CODE:
        for detail in error.details:
            lines.append(f"  → {detail}")
        lines.append(
            f"  Remediation: fix `{NOT_CODE_PATH}` (project/config.yaml) — a "
            "list of path patterns — or remove it for the default."
        )
    elif error.kind == ERROR_TOO_MANY_CHANGED_FILES:
        lines.append(f"  → {error.message}")
        lines.append(
            "  Remediation: not transient — a retry reads the same cut-short "
            "list. Split the PR, or merge it with "
            '`done-work --bypass "<reason>"`.'
        )
    elif error.kind == ERROR_CHANGED_FILES:
        lines.append(f"  → {error.message}")
        lines.append("  Remediation: transient gh failure reading the PR's changed files — retry.")
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


def _find_pr_for_branch(branch: str, config: dict) -> dict | None:
    proc = gh_run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number,isDraft,headRefName,baseRefName",
        ],
        config,
        check=False,
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
        config,
        check=False,
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
