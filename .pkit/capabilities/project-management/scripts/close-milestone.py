#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — close-milestone (verb-subject per DEC-020).

Closes a GitHub Milestone through the validated path, mirroring
`create-milestone` (the milestone verb shape) and `close-issue` (the
close/gate/audit-note pattern). The point of the wrapper is that it holds
the grant a raw `gh api -X PATCH .../milestones/<n> state=closed` lacks:
it runs the membership gate (DEC-021), the foreign-repo mutation guard
(COR-039), and routes the mutation through the shared `_lib.gh` seam
(DEC-023 host/owner pinning) — the path the `agent:project-manager`
`issue-tracker-write` deny discourages doing by hand.

Close-trigger semantics per [project-management:DEC-016-time-bound-containers]
and schemas/time-containers.yaml (READ, not re-decided here):

  * content-based — closes ONLY when every child issue is closed. An open
    child holds the close (hard refuse, exit 1) unless --force.
  * date-based — the date is the trigger; the Milestone closes regardless
    of how many children are still open, and open children roll forward to
    the next Milestone. This wrapper WARNS about open children and lists
    them, then closes; it does NOT itself perform the rollforward
    reassignment (no rollforward routine exists in the capability yet —
    see the GAP note below).
  * either — closes on whichever fires first. With open children present
    this wrapper treats it like content-based (refuse unless --force),
    since the content path closes with no open children; --force closes it
    as a date-triggered close with the same rollforward warning.

The trigger is read from the Milestone description's `Close trigger:` first
line (DEC-016). For an inherited Milestone with no marker, it is inferred
per the schema's fallback_inference: a native due date present ⇒ date-based;
none ⇒ content-based (the inference is announced).

Membership children are resolved the same way the rest of the capability
does — the union of (a) issues carrying the native GitHub Milestone field
for this milestone and (b) issues whose body carries the textual
`Milestone: [#<n>](../milestone/<n>)` ref (the form create-issue writes).

Audit note: a GitHub Milestone has no comment thread (unlike an issue), so
the audit line is appended to the Milestone's description in the SAME PATCH
that flips state=closed — the substrate-appropriate analogue of the closing
comment the other lifecycle wrappers post. Re-append is guarded so a re-run
is idempotent.

GAP (flagged for follow-up, out of this change's touch-set):
  * Rollforward automation. date-based / either closes should reassign open
    children to the rollforward-target Milestone (schema
    rollforward_behaviour + parent_follow_rule). No rollforward routine
    exists in the capability today; this wrapper only warns + lists the open
    children so they can be reassigned by hand. Wiring the reassignment
    cascade is a separate feature.
  * Cascade-eligibility surfacing. Surfacing "milestone now closeable"
    from close-issue's closure cascade when the last child EPIC closes
    (mirroring parent-close eligibility) would require editing close-issue.py,
    which is outside this change's touch-set. Left for a follow-up.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/close-milestone.py 6

Or via the dispatcher (per COR-021):
  pkit project-management close-milestone 6

Exit codes:
  0  closed (or dry-run / already-closed noop)
  1  membership refusal / session refusal / content-based open-children refusal
  2  usage error (milestone not found)
  3  gh failure
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import session_guard  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.milestone import resolve_milestone  # noqa: E402

# The audit marker written into the Milestone description on close. Its
# presence guards re-append so a re-run is idempotent.
_AUDIT_MARKER = "Closed via `pkit project-management close-milestone`"

# The textual milestone-ref create-issue writes into an EPIC's body:
# `Milestone: [#<N>](../milestone/<N>)` (see create-issue._milestone_ref_line).
_MILESTONE_REF_TEMPLATE = r"^Milestone:\s+\[#{n}\]\(\.\./milestone/{n}\)\s*$"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Close a GitHub Milestone through the validated path. Respects "
            "the milestone's close-trigger (content-based / date-based / "
            "either) per time-containers.yaml, posts an audit note, and "
            "supports --dry-run."
        ),
    )
    parser.add_argument(
        "milestone",
        help="Milestone NUMBER (e.g. 6) or exact TITLE to close.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Override the content-based / either open-children refusal; "
            "close despite open child issues (they are NOT auto-rolled-"
            "forward — reassign them by hand)."
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

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before any gh
    # mutation: target repo (cwd) vs session anchor (CLAUDE_PROJECT_DIR).
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    # Resolve the milestone NUMBER. A numeric arg is used directly (so a
    # milestone the open-only resolver would miss still resolves); a title arg
    # goes through the shared resolver (open milestones, number-or-title).
    number = _resolve_number(args.milestone, config)
    if number is None:
        return 2

    milestone = _gh_get_milestone(number, config)
    if milestone is None:
        return 2

    title = str(milestone.get("title", ""))
    state = str(milestone.get("state", "")).lower()
    description = str(milestone.get("description") or "")
    due_on = milestone.get("due_on")

    close_trigger, inferred = _resolve_close_trigger(description, due_on)

    print(f"close-milestone: #{number}")
    print(f"  title:         {title}")
    print(f"  current state: {state}")
    print(f"  close_trigger: {close_trigger}" + (" (inferred)" if inferred else ""))

    if state == "closed":
        print("\n[noop] milestone already closed.")
        return 0

    issue_types = _read_yaml(
        capability_root / "schemas" / "issue-types.yaml", yaml_loader
    )

    children = _gh_list_milestone_children(number, title, config, issue_types)
    if children is None:
        return 3
    open_children = [c for c in children if c["state"] != "closed"]

    print(f"  children:      {len(children)} ({len(open_children)} open)")
    for child in open_children:
        kind = child["type"] or "issue"
        print(f"    - #{child['number']} [{kind}] {child['title']} (open)")

    decision = _decide_close(close_trigger, bool(open_children), args.force)
    if not decision.proceed:
        print(
            "\n[refused] content-based milestone with open child issue(s); "
            "close is held until every child closes.",
            file=sys.stderr,
        )
        print(
            "  → close each open child first, or pass --force to close anyway "
            "(open children are NOT auto-rolled-forward).",
            file=sys.stderr,
        )
        return decision.exit_code

    if decision.rollforward_warning:
        print(
            f"\n[warn] {close_trigger} close with {len(open_children)} open "
            "child issue(s). Per time-containers.yaml the date is the trigger "
            "and open children roll forward to the next Milestone — but this "
            "wrapper does NOT perform the rollforward reassignment. Reassign "
            "the open children above to the rollforward-target Milestone by "
            "hand (e.g. `pkit project-management set-field <n> --parent ...` "
            "or `gh issue edit <n> --milestone ...`).",
            file=sys.stderr,
        )

    new_description = _compose_close_description(
        description,
        close_trigger=close_trigger,
        closed_count=len(children) - len(open_children),
        open_count=len(open_children),
    )

    if args.dry_run:
        closed_count = len(children) - len(open_children)
        audit = _audit_line(close_trigger, closed_count, len(open_children))
        print("\n[dry-run] gh would be invoked; nothing written.")
        print("  would PATCH state=closed and append the audit line:")
        print(f"    {audit}")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Close this milestone? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    if not _gh_close_milestone(number, new_description, config):
        return 3

    print(f"\n[ok] closed milestone #{number} ({close_trigger}).")
    return 0


# ---- close-trigger resolution ---------------------------------------


def _parse_close_trigger(description: str) -> str | None:
    """Return the declared close-trigger from the description's first line.

    Matches the DEC-016 `Close trigger: <value>` marker on the first
    non-blank line; returns None when the marker is absent (an inherited
    Milestone) so the caller can fall back to inference.
    """
    for line in description.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^Close trigger:\s+(date-based|content-based|either)$", s)
        return m.group(1) if m else None
    return None


def _infer_close_trigger(due_on: object) -> str:
    """Infer the close-trigger for an inherited Milestone with no marker.

    Per time-containers.yaml fallback_inference: a native due date present
    ⇒ date-based; none ⇒ content-based.
    """
    return "date-based" if due_on else "content-based"


def _resolve_close_trigger(description: str, due_on: object) -> tuple[str, bool]:
    """Resolve (close_trigger, inferred): declared marker wins, else inferred."""
    declared = _parse_close_trigger(description)
    if declared is not None:
        return declared, False
    return _infer_close_trigger(due_on), True


# ---- close decision (pure policy) -----------------------------------


@dataclass(frozen=True)
class CloseDecision:
    """The trigger-policy verdict for a close attempt (confirmation aside).

    proceed             — go ahead and close (main still applies the --yes /
                          interactive confirmation gate).
    exit_code           — exit code when NOT proceeding (a refusal).
    rollforward_warning — True when closing with open children under a
                          date-driven trigger (the schema rolls them forward;
                          this wrapper only warns — see the module GAP note).
    """

    proceed: bool
    exit_code: int = 0
    rollforward_warning: bool = False


def _decide_close(close_trigger: str, has_open_children: bool, force: bool) -> CloseDecision:
    """Decide whether to close, per the milestone's close-trigger.

    No open children ⇒ always proceed (a clean close for any trigger).
    Open children:
      * content-based / either — hard refuse (exit 1) unless --force.
      * date-based             — proceed with a rollforward warning (the date
                                 is the trigger; children roll forward).
    """
    if not has_open_children:
        return CloseDecision(proceed=True)
    if close_trigger == "date-based":
        return CloseDecision(proceed=True, rollforward_warning=True)
    # content-based / either: open children hold the close unless forced.
    if force:
        return CloseDecision(proceed=True, rollforward_warning=True)
    return CloseDecision(proceed=False, exit_code=1)


# ---- audit note -----------------------------------------------------


def _audit_line(close_trigger: str, closed_count: int, open_count: int) -> str:
    """Compose the one-line audit note appended to the Milestone description."""
    today = _dt.date.today().isoformat()
    tail = f"; {open_count} rolled forward" if open_count else ""
    return (
        f"{_AUDIT_MARKER} on {today} "
        f"(trigger: {close_trigger}; {closed_count} child issue(s) closed{tail})."
    )


def _compose_close_description(
    description: str, *, close_trigger: str, closed_count: int, open_count: int
) -> str:
    """Append the audit line to the description; idempotent on re-run.

    A Milestone has no comment thread, so the audit note lives in the
    description (written in the same PATCH that flips state=closed). If the
    audit marker is already present the description is returned unchanged so a
    re-run does not stack notes.
    """
    if _AUDIT_MARKER in description:
        return description
    line = _audit_line(close_trigger, closed_count, open_count)
    if description.strip():
        return description.rstrip() + "\n\n" + line
    return line


# ---- gh helpers -----------------------------------------------------


def _resolve_number(arg: str, config: dict) -> int | None:
    """Resolve the milestone argument to a NUMBER (numeric direct, else title)."""
    if arg.strip().lstrip("-").isdigit():
        return int(arg)
    resolved = resolve_milestone(arg, config)
    if resolved is None:
        print(
            f"error: no open milestone matches {arg!r}. Pass the milestone "
            "number, or the exact title of an open milestone.",
            file=sys.stderr,
        )
        return None
    return resolved.number


def _gh_get_milestone(number: int, config: dict) -> dict | None:
    """GET a single milestone via `gh api` (validated `_lib.gh` seam)."""
    try:
        proc = gh_run(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/milestones/{number}"],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: could not fetch milestone #{number} "
            f"(gh exit {proc.returncode}).\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"error: gh returned non-JSON for milestone #{number}.", file=sys.stderr)
        return None
    return data if isinstance(data, dict) else None


def _gh_list_milestone_children(
    number: int, title: str, config: dict, issue_types: dict
) -> list[dict] | None:
    """Resolve the milestone's child issues — the union of native + textual.

    A child is any issue that either (a) carries the native GitHub Milestone
    field for this milestone (matched on number or title, the same field
    show-tree reads) or (b) carries the textual `Milestone: [#<n>](../
    milestone/<n>)` body ref create-issue writes. `gh issue list` returns
    issues only (PRs excluded), so no PR filtering is needed.

    Returns a list of `{number, title, state, type}` dicts (state lower-cased,
    type inferred from the title prefix), or None on gh failure.
    """
    try:
        proc = gh_run(
            [
                "gh", "issue", "list", "--state", "all", "--limit", "500",
                "--json", "number,title,state,body,milestone",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: gh issue list failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        rows = json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        print("error: gh issue list returned malformed JSON.", file=sys.stderr)
        return None

    ref_regex = re.compile(_MILESTONE_REF_TEMPLATE.format(n=number), re.MULTILINE)
    children: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        num = row.get("number")
        if not isinstance(num, int):
            continue
        body = str(row.get("body") or "")
        if not (
            _native_milestone_matches(row.get("milestone"), number, title)
            or ref_regex.search(body)
        ):
            continue
        row_title = str(row.get("title", ""))
        children.append(
            {
                "number": num,
                "title": row_title,
                "state": str(row.get("state", "")).lower(),
                "type": _infer_structural_type(row_title, issue_types),
            }
        )
    children.sort(key=lambda c: c["number"])
    return children


def _native_milestone_matches(milestone: object, number: int, title: str) -> bool:
    """True when an issue's native milestone field names this milestone.

    Matched on number OR title — gh's `--json milestone` payload may carry
    either depending on the field set; either identifying this milestone
    counts.
    """
    if not isinstance(milestone, dict):
        return False
    if milestone.get("number") == number:
        return True
    return bool(title) and milestone.get("title") == title


def _gh_close_milestone(number: int, description: str, config: dict) -> bool:
    """PATCH the milestone to state=closed (+ audit description) via `gh_run`.

    Routes the mutation through the shared `_lib.gh` seam — the validated path
    that pins the adopter's host/owner (DEC-023) and that the wrapper's grant
    covers, rather than a raw `gh api` the agent deny discourages.
    """
    args = [
        "gh", "api",
        "-X", "PATCH",
        f"repos/{{owner}}/{{repo}}/milestones/{number}",
        "-f", "state=closed",
        "-f", f"description={description}",
    ]
    try:
        proc = gh_run(args, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: gh failed closing milestone #{number} "
            f"(exit {proc.returncode}).\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


# ---- structural-type inference (mirrors close-issue) ----------------


def _infer_structural_type(title: str, issue_types: dict) -> str | None:
    types = issue_types.get("types") or {}
    for type_name, entry in types.items():
        if not isinstance(entry, dict):
            continue
        prefix = entry.get("title_prefix", "")
        case = entry.get("title_case", "title")
        rendered = str(prefix)
        if case == "upper":
            rendered = rendered.upper()
        if title.startswith(f"[{rendered}] "):
            return str(type_name)
    return None


# ---- I/O helpers ----------------------------------------------------


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
