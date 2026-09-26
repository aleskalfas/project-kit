#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — handoff-issue (DEC-026 workflow wrapper).

Reassigns an in-flight issue from one team member to another without
changing the issue's lifecycle state. Per DEC-026:

    handoff-issue <N> --to @<new-assignee> --reason "<R>"

Gates per DEC-026:
  - Current user is a team member (DEC-021); open-mode supports the
    operation as self-service ownership transfer.
  - Issue currently in `In Progress` or `Review`.

Side-effects, in order:
  - Posts audit comment: `Handoff: @<from> → @<to> (YYYY-MM-DD, reason: <text>)`,
    BEFORE the reassignment so the justification survives a failed edit. It
    closes with a hidden `<!-- pkit-audit-key: handoff-issue:<digest> -->`
    hashed from the from/to pair, the stripped reason, and the issue's count of
    assignment events (assigned + unassigned) read just before posting. A
    successful handoff adds at least one such event and a failed one adds
    none, so a retry of a failed attempt reproduces the comment exactly and
    posts nothing new, while a later handoff identical in from, to and reason
    (A→B, B→A, A→B again) renders a different comment and is recorded. The
    post-once rule is the shared `_lib.comment.post_audit_once` (#902): only a
    comment with exactly that body, posted unedited by the account `gh` posts
    as, counts.
  - `gh issue edit --add-assignee <to> --remove-assignee <from>`.
  - No `move-issue` call (no state transition).

Exit codes:
  0  handed off
  1  membership refusal
  2  usage error / gate failure / gh failure
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate  # noqa: E402
from _lib.audit import audit_key  # noqa: E402
# The one fetch / scan / post-once wiring every audit writer shares (#902).
from _lib.comment import post_audit_once  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


# The handoff audit comment's first-line kind marker. It says WHAT the comment
# is; it is not what makes the post idempotent — the stamp this replaced
# (`<!-- pkit-hook: handoff-issue:<from>-><to> -->`, matched as a substring in
# anyone's comment) let any commenter suppress the record and let a later
# handoff identical in from/to find the first and record nothing (#902).
HANDOFF_AUDIT_MARKER = "<!-- pkit-hook: handoff-issue -->"
# The `_lib.audit.audit_key` writer name for the handoff audit.
HANDOFF_AUDIT_WRITER = "handoff-issue"

# One GraphQL round-trip for the issue's assignment-event count (a totalCount,
# so no pagination). `{owner}` / `{repo}` are `gh api` placeholders resolved from
# the current repository, the same repository `gh issue view` reads.
_ASSIGNMENT_EVENTS_QUERY = (
    "query($owner: String!, $name: String!, $number: Int!) {"
    " repository(owner: $owner, name: $name) {"
    " issue(number: $number) {"
    " timelineItems(itemTypes: [ASSIGNED_EVENT, UNASSIGNED_EVENT]) { totalCount }"
    " } } }"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reassign an in-flight issue from one team member to another. "
            "No state transition; audit comment records the handoff."
        ),
    )
    parser.add_argument("issue_number", type=int)
    parser.add_argument(
        "--to", required=True, dest="new_assignee",
        help="New assignee (`@user` or `user`).",
    )
    parser.add_argument(
        "--reason", required=True,
        help="Reason for the handoff — recorded in the audit comment.",
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
    if not bootstrap_gate.enforce("handoff-issue", capability_root=capability_root):
        return 2

    new_assignee = args.new_assignee.lstrip("@").strip()
    if not new_assignee:
        print("error: --to must name a non-empty assignee.", file=sys.stderr)
        return 2
    reason = args.reason.strip()
    if not reason:
        print(
            "error: --reason must be non-empty (per DEC-026 audit-trail discipline).",
            file=sys.stderr,
        )
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        # Open-mode falls through; closed-mode refuses.
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before any gh
    # mutation: target repo (cwd) vs session anchor (CLAUDE_PROJECT_DIR).
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    # Gate: issue is In Progress or Review (state inferred from milestone/labels
    # in the substrate; here we use a simple heuristic — issue must be open).
    state = str(issue.get("state", "")).lower()
    if state != "open":
        print(
            f"error: issue #{args.issue_number} is in state {state!r}; "
            "handoff only applies to open issues currently in In Progress or Review.",
            file=sys.stderr,
        )
        return 2

    # Determine current assignee (for the audit comment + remove flag).
    assignees = issue.get("assignees") or []
    current_assignees = [
        a.get("login") for a in assignees
        if isinstance(a, dict) and a.get("login")
    ]
    from_assignee = current_assignees[0] if current_assignees else "(unassigned)"

    if from_assignee == new_assignee:
        print(
            f"  #{args.issue_number} is already assigned to @{new_assignee}; "
            "no-op."
        )
        return 0

    print(f"handoff-issue: #{args.issue_number}")
    print(f"  from:   @{from_assignee}")
    print(f"  to:     @{new_assignee}")
    print(f"  reason: {reason}")

    if args.dry_run:
        print("(dry-run: would post audit comment + reassign.)")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # Audit comment, BEFORE the reassignment, posted at most once per handoff.
    if not _post_handoff_audit(
        args.issue_number, from_assignee, new_assignee, reason, config
    ):
        return 2

    # Reassign.
    if not _reassign(args.issue_number, from_assignee, new_assignee, config):
        return 2

    print(f"\n[ok] handed off #{args.issue_number}: @{from_assignee} → @{new_assignee}")
    return 0


# ---- helpers -----------------------------------------------------------


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(
        issue_number, config,
        fields="title,state,assignees,labels,milestone",
    )


def _assignment_event_count(issue_number: int, config: dict) -> int | None:
    """How many assigned + unassigned events the issue's timeline holds, or None
    when that cannot be read.

    It is the handoff audit key's "has a handoff landed since?" component: a
    successful `gh issue edit --add-assignee/--remove-assignee` adds at least one
    event, a failed one adds none. Assignments made outside pkit also add events,
    which only ever makes a later handoff post again. An unreadable count
    contributes an empty key component, which differs from every key minted with
    a readable one, so a retry across that boundary posts again.
    """
    try:
        proc = gh_run(
            [
                "gh", "api", "graphql",
                "-F", "owner={owner}",
                "-F", "name={repo}",
                "-F", f"number={issue_number}",
                "-f", f"query={_ASSIGNMENT_EVENTS_QUERY}",
            ],
            config, check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
        count = data["data"]["repository"]["issue"]["timelineItems"]["totalCount"]
    except (TypeError, ValueError, KeyError):
        return None
    return count if isinstance(count, int) and not isinstance(count, bool) else None


def _post_handoff_audit(
    issue_number: int,
    from_assignee: str,
    to_assignee: str,
    reason: str,
    config: dict,
) -> bool:
    """Post the handoff audit comment unless that exact comment is already there.

    Reads the assignment-event count, renders the keyed body, and posts it
    through the shared `_lib.comment.post_audit_once` (#902). The count grows
    only when a handoff lands, so a retry of a failed attempt reproduces the
    comment exactly and skips, while a later handoff identical in from, to and
    reason posts its own. True when posted or already present; False when a
    needed post failed (the caller then aborts before reassigning).
    """
    key = _handoff_audit_key(
        from_assignee, to_assignee, reason,
        _assignment_event_count(issue_number, config),
    )
    body = _handoff_audit_body(
        from_assignee, to_assignee, reason, dt.date.today().isoformat(), key,
    )
    return post_audit_once(
        "issue", issue_number, key, body, config,
        run=gh_run,
        present_note="handoff audit comment already present; idempotent skip",
    )


def _handoff_audit_key(
    from_assignee: str, to_assignee: str, reason: str, assignment_events: int | None
) -> str:
    """The idempotency key for one handoff (#902): from, to, the stripped reason,
    and the assignment-event count read before posting (see
    `_assignment_event_count`)."""
    return audit_key(
        HANDOFF_AUDIT_WRITER,
        from_assignee,
        to_assignee,
        reason.strip(),
        "" if assignment_events is None else str(assignment_events),
    )


def _handoff_audit_body(
    from_assignee: str, to_assignee: str, reason: str, today: str, key: str
) -> str:
    """The handoff audit comment: kind marker, the handoff line, idempotency key."""
    return (
        f"{HANDOFF_AUDIT_MARKER}\n\n"
        f"Handoff: @{from_assignee} → @{to_assignee} "
        f"({today}, reason: {reason.strip()})\n\n"
        f"{key}"
    )


def _reassign(
    issue_number: int, from_assignee: str, to_assignee: str, config: dict
) -> bool:
    cmd = ["gh", "issue", "edit", str(issue_number), "--add-assignee", to_assignee]
    if from_assignee and from_assignee != "(unassigned)":
        cmd += ["--remove-assignee", from_assignee]
    proc = gh_run(cmd, config, check=False)
    if proc.returncode != 0:
        print(
            f"error: gh issue edit reassignment failed: {proc.stderr.strip()}",
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


if __name__ == "__main__":
    sys.exit(main())
