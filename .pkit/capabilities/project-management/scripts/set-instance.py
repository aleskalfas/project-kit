#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — set-instance.

Set (or show / clear) THIS clone's numeric instance identity — the opt-in
per-clone id the instance-ownership feature keys on (DEC-035 point 1). Written to
a git-ignored runtime file under the capability's ``project/instance/`` directory;
a clone with no id set behaves exactly like a single-clone repo (no ownership
marking, no clash guard, no signed listing). The presence of the id is the sole
activation gate.

This sets *which clone am I* only. It does not touch any issue — the per-issue
ownership marker is written by the lifecycle commands, which read this id:
create-issue claims each issue it files, start-work claims an issue no instance
owns, and close-issue releases the owner as the issue closes (done-work through
the close-issue it runs). handoff-issue does not move the marker yet.

In a project with a topology of seats, a clone's number is its seat's, derived
from the topology, and never typed (DEC-059 point 6). So a number is refused
where the default branch holds a topology, and where the default branch cannot
be resolved, since whether it holds one cannot then be told (COR-054 point 4).
A clone there takes a seat instead (`take-seat`). `--show` also names the seat
the clone took, and `--clear` keeps it.

Usage:
  set-instance <N>       set this clone's instance id (positive integer)
  set-instance --show    print the current id (or `unset`)
  set-instance --clear   unset (revert to the no-op default)

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/set-instance.py

Exit codes:
  0  ran cleanly
  1  refused: the project has a topology, or the default branch cannot be
     resolved, or the foreign-repo guard refused
  2  capability not installed at the expected path
  3  bad argument (no id and no --show/--clear, or a non-positive id)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, session_guard, topology
from _lib.instance_identity import (
    clear_instance_id,
    read_instance_id,
    read_seat_hint,
    write_instance_id,
)
from _lib.membership import CAPABILITY_NAME, resolve_capability_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set this clone's instance id (opt-in, per-clone; DEC-035).",
    )
    parser.add_argument(
        "instance",
        nargs="?",
        type=int,
        help="Instance number to set for this clone (positive integer).",
    )
    parser.add_argument(
        "--show", action="store_true", help="Print the current instance id and exit."
    )
    parser.add_argument("--clear", action="store_true", help="Unset this clone's instance id.")
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
        print(f"instance: {current}" if current is not None else "instance: unset")
        seat = read_seat_hint(capability_root)
        if seat is not None:
            print(f"seat: {seat}, as this clone took it (`pkit pm seats` shows its holder)")
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
        refusal = typed_number_refusal(capability_root)
        if refusal is not None:
            print(refusal, file=sys.stderr)
            return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034): both --clear and a set write
    # the runtime file under capability_root, which --capability-root (or a cwd-walk)
    # can point at a DIFFERENT repo than the session anchor. Gate the write — refuse
    # under autonomy, prompt interactively — unless the operator confirms override.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    if args.clear:
        removed = clear_instance_id(capability_root)
        print(
            "cleared this clone's instance id (now a non-participating clone)."
            if removed
            else "no instance id was set — nothing to clear."
        )
        return 0

    path = write_instance_id(capability_root, args.instance)
    print(f"this clone is now instance {args.instance}.")
    print(f"  written: {path} (git-ignored — never committed)")
    return 0


def typed_number_refusal(
    capability_root: Path,
    *,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
) -> str | None:
    """Why no number may be typed into this clone, or None where one may.

    A project whose default branch holds a topology numbers each clone by its
    seat (DEC-059 point 6). Where the default branch cannot be resolved, whether
    it holds one cannot be told, and no number is typed on a guess (COR-054
    point 4)."""
    try:
        found = topology.read(capability_root, run=run, git=git)
    except topology.Unresolved as exc:
        return (
            f"[refused] set-instance: whether the project has a topology could not be read "
            f"from the default branch ({exc}), so no number is typed into this clone."
        )
    if found is None:
        return None
    return (
        f"[refused] set-instance: {found.where()} holds a topology, so a clone's number is "
        "its seat's, derived from the topology, and never typed (DEC-059 point 6). Take a "
        "seat instead: `pkit pm take-seat`."
    )


if __name__ == "__main__":
    sys.exit(main())
