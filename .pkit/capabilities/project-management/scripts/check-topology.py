#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — check-topology (DEC-059 points 1 to 3, DEC-061 point 10).

Checks the topology a change declares, `project/topology.yaml` in the working
tree, against the topology it would replace: the default branch's, read at the
commit the backbone resolves it to (COR-054 point 5), or the base named for
this run with `--base` or by a pipeline (COR-054 point 3). It says which commit
it read. Each of these fails the check:

- a shape the schema refuses (`schemas/topology.schema.json`)
- a seat name used twice, or more than one organizer seat
- a seat that names no state issue and is not retired, or two seats naming one
- a scope that names a workstream or a type the project does not declare
- a seat that names a pool the topology does not declare, a seat that names
  pools where the topology declares none, and a planner's seat that names any
  pool (DEC-061 point 10)
- a topology under the `label` ownership substrate (DEC-059 point 9)
- a seat of the base deleted or moved rather than retired (point 6)
- a base that cannot be resolved, while the working tree holds a topology

It compares a change with a base, so it is a check of a change and no member of
`pkit validate` (ADR-058 point 7). Read-only and offline: it reads this clone
and no GitHub. A working tree with no topology fails only where the base holds
one, which the change then deletes.

Usage:
  pkit pm check-topology [--base <ref>]

Exit codes:
  0  no problem found
  1  a problem found
  2  usage error: the capability is not found, or not bootstrapped
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, topology
from _lib.membership import CAPABILITY_NAME, resolve_capability_root

VERB = "check-topology"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check project/topology.yaml against the topology of the default branch, or of "
            "--base (DEC-059). Read-only."
        ),
    )
    parser.add_argument(
        "--base",
        default=None,
        help="The base to compare with for this run (default: the default branch).",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    if not bootstrap_gate.enforce("check-topology", capability_root=capability_root):
        return 2
    return say(topology.check_change(capability_root, args.base))


def say(report: topology.Report) -> int:
    """Print what the check found, and return its exit code."""
    tree = report.topology
    if tree is None:
        print(f"{VERB}: no topology at {topology.TOPOLOGY_RELATIVE}")
    else:
        retired = len(tree.seats) - len(tree.active)
        print(
            f"{VERB}: {topology.TOPOLOGY_RELATIVE}, {len(tree.seats)} seat(s)"
            + (f", {retired} retired" if retired else "")
        )
    if report.base is not None and report.base.commit is not None:
        print(f"  base: {report.base.ref} at {report.base.commit}")
    for note in report.notes:
        print(f"note   {note}")
    for problem in report.problems:
        print(f"error  {problem.message}")
    if report.failed:
        print(f"\n{len(report.problems)} problem(s) found.")
        return 1
    print("\n[ok] no problem found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
