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
  - `gh pr merge --squash --subject <PR title>` — WITHOUT `--delete-branch`:
    that flag makes gh check out the default branch locally and delete the
    local head, and the whole command exits non-zero when the working tree
    cannot do so (a detached HEAD; the head branch checked out in a worktree,
    #587) — after the remote merge has already landed.
  - `after_merge_pr` hooks (DEC-024) IMMEDIATELY after the merge, so no
    best-effort step stands between the irreversible merge and them.
  - Best-effort branch cleanup: delete the remote head ref through the API,
    then `git checkout <default_branch>`, `git pull --ff-only`, `git branch
    -D <head>`. Each step warns with its reason and continues; none can fail
    the run — a head branch checked out in a worktree simply leaves a
    warning where the local delete would have been.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/merge-pr.py 99

Or via the dispatcher (per COR-021):
  pkit project-management merge-pr 99

Exit codes:
  0  merged (or dry-run reported)
  1  membership / checkbox / title / CI-status refusal
  2  usage error (PR not found)
  3  gh failure
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate  # noqa: E402
from _lib import pr_merge  # noqa: E402
from _lib.ci_checks import evaluate_ci_gate  # noqa: E402
# DEC-007's checkbox close-gate — the ONE implementation (`_lib.checkbox_gate`),
# shared with close-issue, done-work and the engine predicate.
from _lib.checkbox_gate import unticked_boxes as _unticked_boxes  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.hooks import fire_hooks  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    Identity,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


CLOSING_KEYWORD_RE = re.compile(
    r"\b(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE
)

# Idempotency stamp for the CI-bypass audit comment (mirrors done-work's
# BYPASS_AUDIT_STAMP shape; a distinct marker so a re-run recognises its own
# prior comment rather than confusing it with an approval-gate bypass).
CI_BYPASS_AUDIT_STAMP = "<!-- pkit-hook: merge-pr-ci-bypass -->"


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
            "checks). Use only when authorised."
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
            "clears a red or pending CI check."
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
    # merge: target repo (cwd) vs session anchor (CLAUDE_PROJECT_DIR).
    if not session_guard.enforce(override=args.allow_foreign_repo):
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

    if pr_state != "open":
        print(
            f"\n[refused] PR is not open (state: {pr_state}). "
            "Cannot merge.",
            file=sys.stderr,
        )
        return 1

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
    print(
        f"  closes: {', '.join(f'#{n}' for n in closing_issues) or '<none>'}"
    )
    if not closing_issues:
        print(
            "\n[refused] PR body has no `Closes #N` / `Fixes #N` / "
            "`Resolves #N` reference (required by git-conventions.yaml).\n"
            "  → add a `Closes #<N>` line to the PR body and retry.",
            file=sys.stderr,
        )
        return 1

    if not args.skip_checkbox_gate:
        unticked_findings = _gather_unticked_findings(args.pr_number, pr_body, closing_issues, config)
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

    if args.dry_run:
        note = ""
        if not ci_gate.passing:
            note = " (would post CI-bypass audit comment first)"
        print(
            f"\n[dry-run] gh pr merge --squash --subject {pr_title!r} would "
            f"be invoked{note}, then the remote head branch deleted and the "
            "local checkout tidied; nothing written."
        )
        return 0
    if not args.yes and sys.stdin.isatty():
        reply = input("Squash-merge and delete the head branch? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # Post the CI-bypass audit comment before merging so the trail survives
    # even if the merge later fails (bypassable-with-audit; the comment lands
    # first per validation-severity.yaml).
    if not ci_gate.passing and args.bypass_ci:
        if not _post_ci_bypass_audit(
            args.pr_number, args.bypass_ci.strip(), invoker, ci_gate.failing_checks, config
        ):
            print(
                "[warn] could not post CI-bypass audit comment; aborting "
                "before merge.",
                file=sys.stderr,
            )
            return 3

    # Squash-merge with the PR title as the landed subject (DEC-013; #33).
    # No `--delete-branch`: the mechanic is `_lib.pr_merge`'s — the one
    # implementation `done-work` also runs (#882).
    if not pr_merge.squash_merge(
        args.pr_number, pr_title=pr_title, admin=args.admin, config=config,
    ):
        return 3

    print(f"\n[ok] merged: {pr_url}")

    # Fire after_merge_pr hooks per DEC-024 — FIRST, before any best-effort
    # branch cleanup, so a cleanup warning can never stand between the
    # irreversible merge and the hooks.
    fire_hooks(
        "after_merge_pr",
        context={
            "pr": {
                "number": args.pr_number,
                "title": str(pr.get("title", "")) if pr else "",
            },
        },
        config=config,
        capability_root=capability_root,
    )

    # Branch cleanup — best-effort, never fatal. The remote head ref goes
    # through the API (no local-checkout dependency); the local steps warn
    # and continue, so a head branch checked out in a worktree (#587) is a
    # warning on the local delete, not a failed merge.
    head_branch = str(pr.get("headRefName") or "")
    if head_branch:
        pr_merge.delete_remote_branch(head_branch, config)
        pr_merge.cleanup_local(head_branch, config)
    else:
        print(
            "[warn] PR reports no head branch; skipping branch cleanup.",
            file=sys.stderr,
        )

    return 0


# ---- closing-issue parsing -----------------------------------------


def _extract_closing_issues(pr_body: str) -> list[int]:
    """Find all `Closes #N` / `Fixes #N` / `Resolves #N` numbers."""
    out: list[int] = []
    for m in CLOSING_KEYWORD_RE.finditer(pr_body or ""):
        n = int(m.group(1))
        if n not in out:
            out.append(n)
    return out


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


def _ci_bypass_audit_body(
    invoker: Identity, reason: str, failing_checks: tuple[str, ...]
) -> str:
    """Render the bypassable-with-audit comment body (validation-severity.yaml).

    Follows the schema's `audit_comment_template`
    (`Bypassed by <name> <<email>>: <reason>`), naming the checks the bypass
    overrode so the trail records *what* was skipped. Prefixed with the
    idempotency stamp so a re-run recognises its own prior comment.
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
    pr_number: int,
    reason: str,
    invoker: Identity,
    failing_checks: tuple[str, ...],
    config: dict,
) -> bool:
    """Post the CI-bypass audit comment to the PR, idempotently.

    Returns True on success (or when an identical audit comment is already
    present — the stamp makes the post idempotent), False on gh failure.
    """
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
                "title,body,state,url,headRefName,baseRefName,statusCheckRollup",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: gh pr view {pr_number} failed.\n"
            f"stderr: {proc.stderr.strip()}",
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
