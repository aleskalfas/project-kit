#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Project-management capability — set-instance.

Set (or show / clear) THIS clone's numeric instance identity — the opt-in
per-clone id the instance-ownership feature keys on (DEC-035 point 1). Written to
a git-ignored runtime file under the capability's ``project/instance/`` directory;
a clone with no id set behaves exactly like a single-clone repo (no ownership
marking, no clash guard, no signed listing). The presence of the id is the sole
activation gate.

This sets *which clone am I* only. It does not touch any issue — the per-issue
ownership marker is written by the lifecycle commands (create-issue / start-work /
handoff-issue), which read this id.

A clone includes its linked git worktrees: a worktree with no id of its own
reads the main working tree's. Setting and clearing act on the local file only,
so a worktree can take a number of its own and clear it again.

Usage:
  set-instance <N>       set this clone's instance id (positive integer)
  set-instance --show    print the current id (or `unset`), and where a
                         worktree reads its clone's from
  set-instance --clear   unset (revert to the no-op default)

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/set-instance.py

Exit codes:
  0  ran cleanly
  2  capability not installed at the expected path
  3  bad argument (no id and no --show/--clear, or a non-positive id)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, session_guard
from _lib.instance_identity import (
    clear_instance_id,
    identity_path,
    identity_source,
    main_work_tree_identity_path,
    read_instance_id,
    write_instance_id,
)
from _lib.membership import CAPABILITY_NAME, resolve_capability_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Set this clone's instance id, or a linked worktree's own (opt-in; DEC-035)."),
    )
    parser.add_argument(
        "instance",
        nargs="?",
        type=int,
        help=(
            "Instance number to set here (positive integer); in a linked worktree, "
            "a number of the worktree's own."
        ),
    )
    parser.add_argument(
        "--show", action="store_true", help="Print the current instance id and exit."
    )
    parser.add_argument("--clear", action="store_true", help="Unset the instance id set here.")
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
    if not bootstrap_gate.enforce("set-instance", capability_root=capability_root):
        return 2

    if args.show:
        # Read-only — no mutation, so the foreign-repo guard does not apply.
        current = read_instance_id(capability_root)
        source = identity_source(capability_root)
        if current is None and source is not None:
            # A file that cannot be read fails closed to unset; say which one.
            print(f"instance: unset (the id file cannot be read: {source})")
            return 0
        if current is None:
            print("instance: unset")
            return 0
        if source is not None and source != identity_path(capability_root):
            print(f"instance: {current} (the clone's, read from the main working tree: {source})")
        else:
            print(f"instance: {current}")
        return 0

    # Validate arguments before any mutation.
    if not args.clear:
        if args.instance is None:
            print(
                "error: provide an instance number, or use --show / --clear.",
                file=sys.stderr,
            )
            return 3
        if args.instance < 1:
            print("error: instance id must be a positive integer.", file=sys.stderr)
            return 3

    # Foreign-repo mutation guard (COR-039 / ADR-034): both --clear and a set write
    # the runtime file under capability_root, which --capability-root (or a cwd-walk)
    # can point at a DIFFERENT repo than the session anchor. Gate the write — refuse
    # under autonomy, prompt interactively — unless the operator confirms override.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    if args.clear:
        removed = clear_instance_id(capability_root)
        # A worktree that has no id of its own reads its clone's.
        inherited = read_instance_id(capability_root)
        if removed and inherited is None:
            print("cleared this clone's instance id (now a non-participating clone).")
        elif removed:
            print(
                "cleared this worktree's own instance id; it reads its clone's, "
                f"instance {inherited}, from the main working tree."
            )
        elif inherited is None:
            print("no instance id was set — nothing to clear.")
        else:
            print(
                "this worktree has no instance id of its own — nothing to clear. "
                f"It reads its clone's, instance {inherited}, from the main working "
                "tree; clear it there."
            )
        return 0

    path = write_instance_id(capability_root, args.instance)
    if main_work_tree_identity_path(capability_root) is not None:
        print(f"this worktree is now instance {args.instance}, a number of its own.")
    else:
        print(f"this clone is now instance {args.instance}.")
    print(f"  written: {path} (git-ignored — never committed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
