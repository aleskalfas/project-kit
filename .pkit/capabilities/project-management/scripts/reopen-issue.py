#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — reopen-issue (verb-subject per DEC-020).

Reopens a closed GitHub issue. Optional `--reason` records why; the
script posts an audit comment + invokes `gh issue reopen`. Membership
gate per DEC-021 runs at startup.

Reopening puts the issue back into the lifecycle (#1049). `done` is the
workflow's terminal state, so there is no transition out of it; instead the
reopen removes the issue's state label(s), and the issue's position is read
again the way the detectors read any open issue without one: `backlog` when
it has a milestone, `todo` otherwise — the same place a freshly filed or
freshly scheduled issue sits. From there `start-work` (or `promote-issue`)
takes it on as usual. An issue that is already open but still carries the
done label (reopened by hand, or before this reset existed) is repaired the
same way. Where the state is not label-carried — derived from open/closed,
or on a Projects-v2 board — no label is touched; a board status is left for
you to reset, as `move-issue` leaves it.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/reopen-issue.py 42

Or via the dispatcher (per COR-021):
  pkit project-management reopen-issue 42 --reason "regressed"

Exit codes:
  0  reopened or repaired (or dry-run reported, or already open)
  1  membership refusal
  2  usage error (issue not found)
  3  gh failure (a reopen whose state reset failed included — re-run to finish)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_carriage  # noqa: E402
from _lib import axis_labels  # noqa: E402
from _lib import bootstrap_gate  # noqa: E402
from _lib import lifecycle_inference as infer  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reopen a closed GitHub issue.",
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number to reopen.",
    )
    parser.add_argument(
        "--reason",
        default=None,
        help="Free-text reason recorded in the audit comment.",
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
    if not bootstrap_gate.enforce("reopen-issue", capability_root=capability_root):
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

    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    state = str(issue.get("state", "")).lower()
    title = str(issue.get("title", ""))
    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    reset = _plan_state_reset(
        labels,
        milestone=issue.get("milestone"),
        config=config,
        substrate_map=axis_labels.load_substrate_map(capability_root),
    )

    print(f"reopen-issue: #{args.issue_number}")
    print(f"  title:         {title}")
    print(f"  current state: {state}")
    if args.reason:
        print(f"  reason:        {args.reason}")

    closed = state == "closed"
    if not closed and not reset.stuck_at_done:
        print("\n[noop] issue is already open.")
        return 0
    if not closed:
        print("\n  open, but still labelled done — resetting its state.")

    print(f"  state after:   {reset.position}")
    if reset.remove_labels:
        print(f"  - remove label(s): {', '.join(reset.remove_labels)}")
    if reset.note:
        print(f"  [note] {reset.note}")

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0
    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    if closed:
        if args.reason:
            comment_body = (
                f"[reopen] {args.reason}\n\n"
                "Reopened via `pkit project-management reopen-issue`."
            )
            if not _gh_comment(args.issue_number, comment_body, config):
                return 3

        if not _gh_reopen(args.issue_number, config):
            return 3

    if reset.remove_labels and not _gh_remove_labels(
        args.issue_number, reset.remove_labels, config
    ):
        print(
            f"error: #{args.issue_number} is open but its state label(s) could not "
            "be removed, so it still reads as done; re-run reopen-issue to finish.",
            file=sys.stderr,
        )
        return 3

    verb = "reopened" if closed else "repaired"
    print(f"\n[ok] {verb} #{args.issue_number}; its state is now {reset.position}.")
    return 0


@dataclass(frozen=True)
class StateReset:
    """How a reopen puts an issue back into the lifecycle."""

    position: str               # where the detectors read it once open (backlog / todo)
    remove_labels: tuple[str, ...]  # the state label(s) to strip
    stuck_at_done: bool         # an open issue whose state label still reads done
    note: str | None            # why nothing is stripped, where that needs saying


def _plan_state_reset(
    labels: list[str],
    *,
    milestone: dict | None,
    config: dict,
    substrate_map: "axis_labels.SubstrateMap | None",
) -> StateReset:
    """Plan the state reset of a reopen — pure, from the issue's labels.

    Every label carrying `state` is removed, so the detectors' precedence
    (closed → done; state label; milestone → backlog; else todo) reads the
    reopened issue as `backlog` or `todo`. `done` is terminal in workflow.yaml
    and stays so: a reopen re-enters the lifecycle, it does not transition out
    of its end state. Where no label carries `state`, nothing is removed.
    """
    carriage = axis_carriage.carriage("state", config, substrate_map)
    if carriage not in ("kit-label", "adopter-label"):
        note = None
        if carriage == "board":
            note = (
                "the state lives on your Projects-v2 board; reset its Status by "
                "hand (pkit does not write the board state yet)."
            )
        return StateReset(
            position=_open_position(labels, milestone, substrate_map),
            remove_labels=(),
            stuck_at_done=False,
            note=note,
        )
    state_labels = tuple(axis_labels.carried_labels("state", labels, substrate_map))
    remaining = [name for name in labels if name not in state_labels]
    return StateReset(
        position=_open_position(remaining, milestone, substrate_map),
        remove_labels=state_labels,
        stuck_at_done=axis_labels.resolve_read("state", labels, substrate_map) == "done",
        note=None,
    )


def _open_position(
    labels: list[str],
    milestone: dict | None,
    substrate_map: "axis_labels.SubstrateMap | None",
) -> str:
    """Where the detectors read an OPEN issue with these labels — the one home
    of the position read (`lifecycle_inference`), so the reported state is the
    one `start-work` will see."""
    return infer.infer_current_state(
        state="open",
        milestone=milestone,
        labels=labels,
        substrate_map=substrate_map,
    )


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(issue_number, config, fields="title,state,labels,milestone")


def _gh_remove_labels(issue_number: int, labels: tuple[str, ...], config: dict) -> bool:
    cmd = ["gh", "issue", "edit", str(issue_number)]
    for name in labels:
        cmd.extend(["--remove-label", name])
    try:
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue edit (state label reset) failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _gh_comment(issue_number: int, body: str, config: dict) -> bool:
    try:
        proc = gh_run(
            ["gh", "issue", "comment", str(issue_number), "--body", body],
            config,
            check=False,
        )
    except FileNotFoundError:
        return False
    return proc.returncode == 0


def _gh_reopen(issue_number: int, config: dict) -> bool:
    try:
        proc = gh_run(
            ["gh", "issue", "reopen", str(issue_number)],
            config,
            check=False,
        )
    except FileNotFoundError:
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue reopen failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


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
