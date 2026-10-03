#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — decline-use-case-task.

Keep, show or clear the answer that declined the use-case Task in this checkout
(DEC-054 point 5). Over an empty use-case set, batch planning offers a Task to
author the use cases ahead of work that touches what users do. When the user
revises it out of a plan and approves the plan, the project-manager runs this
command, and plans from this checkout leave the Task out for the rest of the day,
in the machine's local time. From the next day on, the Task is offered again.

The answer is the UTC time of the approval, in a git-ignored runtime file under the
capability's ``project/instance/`` directory, so it is never committed and each
clone and worktree keeps its own.

Usage:
  decline-use-case-task                  keep the answer: declined now
  decline-use-case-task --show [--json]  print the kept answer (read-only)
  decline-use-case-task --clear          discard the kept answer

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/decline-use-case-task.py

Exit codes:
  0  ran cleanly (--show, in every state of the answer)
  1  refused: the capability folder is in another repository than the session's
  2  capability not installed at the expected path, or not bootstrapped
  3  bad argument (--show with --clear, or --json without --show)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, session_guard, use_case_task
from _lib.membership import CAPABILITY_NAME, resolve_capability_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Keep, show or clear the answer that declined the use-case Task in this "
            "checkout, until the next local day (DEC-054)."
        ),
    )
    parser.add_argument(
        "--show", action="store_true", help="Print the kept answer and exit (read-only)."
    )
    parser.add_argument("--json", action="store_true", help="With --show: print it as JSON.")
    parser.add_argument("--clear", action="store_true", help="Discard the kept answer.")
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            f"(default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/)."
        ),
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    if args.show and args.clear:
        print("error: --show and --clear do not go together.", file=sys.stderr)
        return 3
    if args.json and not args.show:
        print("error: --json goes with --show only.", file=sys.stderr)
        return 3

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            f"error: {CAPABILITY_NAME} capability not found. Run this from within "
            f"an adopter project with the capability installed.",
            file=sys.stderr,
        )
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("decline-use-case-task", capability_root=capability_root):
        return 2

    now = datetime.now(timezone.utc)
    if args.show:
        # Read-only — no mutation, so the foreign-repo guard does not apply.
        kept = use_case_task.read(capability_root, now)
        if args.json:
            print(json.dumps(use_case_task.document(kept), indent=2))
        else:
            print(use_case_task.describe(kept))
        return 0

    # Foreign-repo mutation guard (COR-039 / ADR-034): keeping and clearing both
    # write under capability_root, which --capability-root (or a cwd-walk) can
    # point at a different repository than the session's. Gate the write unless
    # the operator confirms the override.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    if args.clear:
        removed = use_case_task.clear(capability_root)
        print(
            "cleared: no declined answer is kept now; the next plan offers the Task."
            if removed
            else "nothing to clear: no declined answer was kept."
        )
        return 0

    path = use_case_task.record(capability_root, now)
    print(use_case_task.describe(use_case_task.read(capability_root, now)))
    print(f"  written: {path} (git-ignored — never committed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
