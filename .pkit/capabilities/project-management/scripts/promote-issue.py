#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — promote-issue (DEC-026 workflow wrapper).

Promotes an issue from Todo → Backlog, recording the authorisation source.
Per DEC-026 (as amended for issue #61):

    promote-issue <N> [--milestone "<M>"] --reason "<R>"

Two paths:
  - `--milestone` given → resolves <M> to an OPEN milestone (by number or
    exact title), attaches it via `gh issue edit --milestone`, then calls
    `move-issue --to backlog`.
  - `--milestone` omitted → promotes on `--reason` alone: skips
    `_attach_milestone`, then calls `move-issue --to backlog`. No milestone
    resolution is attempted.

Gates per DEC-026:
  - `--reason` non-empty (the authorisation source — typically the
    user's verbal in-session request; required in both paths).
  - When `--milestone` is given, `<M>` must match the exact title of an
    OPEN milestone in the repo (given-but-unresolvable is still an error;
    it is never silently downgraded to milestone-free).
  - Current Status = Todo (delegated to `move-issue`'s state machine).

Composes over `move-issue.py`: this wrapper attaches the milestone (if any),
then invokes `move-issue --to backlog`, **threading `--reason` to move-issue's
`--bypass-reason`**. Per DEC-049, **move-issue is the sole audit-comment writer**
— it posts the one canonical audit comment (from the schema template); this
wrapper no longer posts its own (ending the #672 double-post).

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/promote-issue.py 42 --reason "PM approved"
  uv run --script .pkit/capabilities/project-management/scripts/promote-issue.py 42 --milestone "v1" --reason "PM approved"

Or via the dispatcher (per COR-021):
  pkit project-management promote-issue 42 --reason "PM approved"
  pkit project-management promote-issue 42 --milestone "v1" --reason "PM approved"

Exit codes:
  0  promoted
  1  membership refusal
  2  usage error / gate failure / gh failure
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate  # noqa: E402
from _lib import axis_carriage  # noqa: E402
from _lib import axis_labels  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.milestone import resolve_milestone  # noqa: E402
from _lib.substrate_writes import write_milestone  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)




def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Promote an issue Todo → Backlog by attaching a Milestone "
            "and posting an audit comment with the authorisation source. "
            "Composes over move-issue (per DEC-026 / DEC-020)."
        ),
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number to promote.",
    )
    parser.add_argument(
        "--milestone",
        default=None,
        help=(
            "OPEN milestone to attach. Accepts the milestone number "
            "(e.g. `6`) or its exact title (e.g. `Milestone 1: ...`). "
            "Optional — omit to promote on --reason alone (no milestone "
            "attached). When given, must match an OPEN milestone exactly; "
            "an unresolvable value is always an error."
        ),
    )
    parser.add_argument(
        "--reason",
        required=True,
        help="Authorisation source — typically the user's in-session request.",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Path to the installed capability's directory (default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan; do not invoke gh or move-issue.",
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

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("promote-issue", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    substrate_map = axis_labels.load_substrate_map(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before any gh
    # mutation / the composed move-issue. A confirmed override is threaded
    # into the move-issue subprocess so the cross-repo gate is confirmed once,
    # not twice.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    # Gate: --reason non-empty (argparse `required` covers empty
    # presence, but the value may still be whitespace-only).
    reason = args.reason.strip()
    if not reason:
        print(
            "error: --reason must be non-empty (per DEC-026 audit-trail discipline).",
            file=sys.stderr,
        )
        return 2

    # Resolve --milestone when given (accepts number OR title; per #217).
    # The title is what downstream `gh issue edit --milestone` wants, so
    # normalise to the title form regardless of input shape.
    # When --milestone is omitted, skip resolution entirely — promoting on
    # --reason alone is a valid path per the DEC-026 #61 amendment.
    milestone_title: str | None = None
    if args.milestone is not None:
        resolved = resolve_milestone(str(args.milestone), config)
        if resolved is None:
            print(
                f"error: milestone {args.milestone!r} did not match any OPEN "
                "milestone (tried as number, then as title). "
                "List with `gh api repos/<owner>/<repo>/milestones?state=open`.",
                file=sys.stderr,
            )
            return 2
        milestone_title = resolved.title

    print(f"promote-issue: #{args.issue_number}")
    if milestone_title is not None:
        print(f"  milestone: {milestone_title}")
    else:
        print("  milestone: (none — promoting on --reason alone)")
    print(f"  reason:    {reason}")

    if args.dry_run:
        if milestone_title is not None:
            print(
                f"(dry-run: would attach milestone {milestone_title!r} and call "
                "move-issue --to backlog, which posts the single audit comment.)"
            )
        else:
            print(
                "(dry-run: would call move-issue --to backlog, which posts the "
                "single audit comment (no milestone — --reason-only path).)"
            )
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # DEC-049: move-issue is the SOLE audit-comment writer. This wrapper no longer
    # posts its own audit comment (which caused the #672 double-post); it passes
    # the authorisation reason to move-issue via `--bypass-reason`, and move-issue
    # posts the one canonical audit comment (rendered from the schema template).

    # Attach the milestone via gh issue edit — only when one was given.
    if milestone_title is not None:
        if not _attach_milestone(args.issue_number, milestone_title, config):
            return 2

    # Detect the issue's current state before calling move-issue. If
    # the issue is already at Backlog or further (cascade may have
    # walked it past Todo), the transition is a no-op — skip the
    # move-issue invocation and exit 0 with an idempotent-skip note.
    # Per #219: previously this path errored with "no transition
    # backlog → backlog declared" and exited 2, forcing callers to
    # special-case the already-promoted state.
    current_state = _detect_current_state(args.issue_number, config, substrate_map)
    if current_state in ("backlog", "in-progress", "review", "done"):
        idempotent_detail = (
            "milestone reattached; no state transition needed"
            if milestone_title is not None
            else "no state transition needed"
        )
        print(
            f"\n[ok] #{args.issue_number} already at {axis_labels.label('state', current_state)} "
            f"({idempotent_detail})."
        )
        return 0

    # Compose over move-issue for the actual state transition. move-issue posts
    # the single canonical audit comment from the reason threaded here (DEC-049).
    rc = _invoke_move_issue(
        args.issue_number, "backlog", reason, args.capability_root, args.allow_foreign_repo
    )
    if rc != 0:
        applied = "milestone" if milestone_title is not None else "(nothing)"
        print(
            f"[warn] {applied} applied; move-issue exited {rc} (no audit comment or "
            "transition). Re-run this wrapper or run `move-issue --to backlog` to complete.",
            file=sys.stderr,
        )
        return rc

    if milestone_title is not None:
        print(f"\n[ok] promoted #{args.issue_number} Todo → Backlog (milestone: {milestone_title})")
    else:
        print(f"\n[ok] promoted #{args.issue_number} Todo → Backlog (no milestone)")
    return 0


def _detect_current_state(
    issue_number: int,
    config: dict,
    substrate_map: axis_labels.SubstrateMap | None = None,
) -> str | None:
    """The issue's current state, read from whichever substrate CARRIES it.

    Returns one of "todo", "backlog", "in-progress", "review", "done", or None
    when the state cannot be read here. Used by `promote-issue` for the
    idempotent-skip path on already-promoted issues (per #219).

    **Carriage is asked first** ([project-management:DEC-051-axis-carriage-
    activation] decision point 4). The previous version read the kit's `state:`
    prefix unconditionally, which was wrong in both directions:

      * a `label`-bound `state` (the adopter's own `Ready` / `Inbox`) was never
        found, so the skip never fired and an already-promoted issue failed with
        "no transition backlog → backlog" — the #219 regression, through a
        substrate #219 predates;
      * under a configured board the kit's `state:*` labels are not the
        substrate, but a STALE one left over from before the board (or from
        another tool) was still trusted — a false skip, which is worse than no
        skip: the promotion silently does not happen.

    Only the two label carriages are readable here, and `resolve_read` covers
    both (greenfield identity, or the adopter's reverse remap). The rest return
    None, which the caller already treats as "unknown, proceed to move-issue" —
    the safe direction, since move-issue re-reads the position through
    `lifecycle_inference` with the full open/closed + milestone signal this
    label-only read does not fetch:

      * `board` — the value is on a Projects-v2 field. This function does NOT
        read it: the board value read (and the rule that an unreadable board
        raises) belongs to the board read-path contract, and is specified there
        but not yet built. Returning nothing is the honest answer until it is.
      * `derived` — open/closed carries it, which needs a signal this label-only
        read does not fetch; `lifecycle_inference.infer_current_state` is the
        home of that read and move-issue performs it.
      * `title` / `degrade` — no label carries the axis.
    """
    carried = axis_carriage.carriage("state", config, substrate_map)
    if carried not in ("kit-label", "adopter-label"):
        return None
    try:
        proc = gh_run(
            ["gh", "issue", "view", str(issue_number), "--json", "labels"],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except (ValueError, KeyError, TypeError):
        return None
    labels = data.get("labels") or []
    names = [
        label.get("name", "") if isinstance(label, dict) else ""
        for label in labels
    ]
    # Through the seam: identity in greenfield, the reverse remap under a
    # `label` binding. Both return the kit's own state vocabulary, which is what
    # the caller's already-promoted tuple is written in.
    return axis_labels.resolve_read("state", names, substrate_map)


# ---- gates --------------------------------------------------------------
#
# `_milestone_exists_open` + `_parse_concatenated_json_arrays` were
# removed in #217 — both moved to `_lib/milestone.py` along with the
# `resolve_milestone(arg, config)` helper that handles either number
# or title input. Call sites switched to the lib resolver.


# ---- side-effects ------------------------------------------------------


def _attach_milestone(issue_number: int, title: str, config: dict) -> bool:
    # Route the milestone write through the sole constructor (ADR-031); apply
    # this script's own report-and-return-bool posture to the neutral result.
    result = write_milestone(config, issue_number=issue_number, title=title)
    if not result.ok:
        print(f"error: {result.detail}", file=sys.stderr)
        return False
    return True


def _invoke_move_issue(
    issue_number: int,
    target: str,
    reason: str,
    capability_root_arg: Path | None,
    allow_foreign_repo: bool,
) -> int:
    """Shell out to `move-issue.py --to <target>` as the substrate transition.

    ``reason`` is the authorisation reason, threaded to move-issue's
    ``--bypass-reason`` so move-issue posts the **single** canonical audit comment
    (DEC-049 — this wrapper no longer posts its own, ending the #672 double-post).

    ``allow_foreign_repo`` threads promote-issue's confirmed cross-repo
    override into the composed move-issue so the foreign-repo gate (COR-039 /
    ADR-034) is confirmed once at the wrapper, not re-prompted by the inner
    transition.
    """
    cmd = [
        sys.executable,
        str(_HERE / "move-issue.py"),
        str(issue_number),
        "--to", target,
        "--bypass",  # Todo → Backlog is bypassable-with-audit per workflow.yaml
        "--bypass-reason", reason,
        "--yes",
    ]
    if allow_foreign_repo:
        cmd.append("--allow-foreign-repo")
    if capability_root_arg is not None:
        cmd += ["--capability-root", str(capability_root_arg)]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


# ---- helpers -----------------------------------------------------------


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
