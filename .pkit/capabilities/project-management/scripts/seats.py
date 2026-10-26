#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — seats (DEC-059 point 3).

Lists the seats of the project's topology, as the default branch holds it at
the commit the backbone resolves it to, and says which commit it read (point
1). For each seat it shows its number, its name, its role, the agent definition
it names, its scope, whether it is the organizer seat or retired, its state
issue and its holder. The holder is read from the seat's state issue through
the state-issue seam (`_lib/state_issues`, ADR-071): an account and a clone's
key, with where the clone lies, or free. The seat this clone holds is marked.

It then names each open state issue of a seat that no seat of the topology
names, such as one a change closed unmerged left, for a person to close on
GitHub (point 3). The open state issues come from the one read of issues, never
GitHub's search.

A read of a state issue restores a marker a hand removed from its description,
the one write a read makes (ADR-071 point 5), so the foreign-repo guard runs
first, after the membership gate (DEC-021) and the bootstrap gate.

Usage:
  pkit pm seats

Exit codes:
  0  listed, or the default branch declares no topology
  1  refused: membership, or the default branch cannot be resolved
  2  usage error: the capability is not found, or not bootstrapped
  3  a seat's state issue, or the listing of open issues, could not be read
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, instance_identity, session_guard, state_issues, topology
from _lib.gh import load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    members_path,
    resolve_capability_root,
    resolve_invoker_identity,
)

VERB = "seats"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List the topology's seats, each with its role and its holder (DEC-059).",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2
    if not bootstrap_gate.enforce("seats", capability_root=capability_root):
        return 2
    config = load_adopter_config(capability_root)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(read_members(capability_root), invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1
    # A read restores a missing marker on a state issue of this repository.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    return list_seats(capability_root, login=invoker.github_login, gh=state_issues.runner(config))


def list_seats(
    capability_root: Path,
    *,
    login: str | None,
    gh: state_issues.Gh,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
    versions: Any = None,
) -> int:
    """Print each seat with its role and its holder, then the state issues no
    seat names. Returns the exit code."""
    try:
        snap = topology.snapshot(
            capability_root,
            gh=gh,
            account=login,
            key=instance_identity.read_clone_key(capability_root),
            run=run,
            git=git,
            versions=versions,
        )
    except topology.Unresolved as exc:
        print(
            f"[refused] {VERB}: the topology could not be read from the default branch ({exc}).",
            file=sys.stderr,
        )
        return 1
    if snap is None:
        print(f"{VERB}: the default branch declares no topology ({topology.TOPOLOGY_RELATIVE}).")
        return 0
    tree = snap.topology
    retired = len(tree.seats) - len(tree.active)
    print(
        f"{VERB}: the topology of {tree.where()}, {len(tree.seats)} seat(s)"
        + (f", {retired} retired" if retired else "")
    )
    for problem in tree.problems:
        print(f"warn: {topology.TOPOLOGY_RELATIVE}: {problem.message}", file=sys.stderr)
    code = 0
    for state in snap.states():
        print(seat_line(state, mine=state.held_by(snap.clone)))
        if state.state == topology.UNREAD and state.seat.state_issue is not None:
            code = 3
    listed = state_issues.list_open(snap.run)
    if listed.rows is None:
        print(f"[error] {listed.cause}, so no stray state issue is named.", file=sys.stderr)
        return 3
    if listed.cut:
        print(
            f"warn: the listing reached {state_issues.OPEN_LIMIT} open issues, so a state issue "
            "past it is not named below.",
            file=sys.stderr,
        )
    strays = stray_state_issues(tree, listed.rows)
    if strays:
        print("\nState issues no seat names, for a person to close (DEC-059 point 3):")
        for number, key in strays:
            print(f"  #{number}  seat {key}")
    return code


def seat_line(state: topology.SeatState, *, mine: bool) -> str:
    """One seat as the listing shows it."""
    seat = state.seat
    marks = [seat.role, f"agent {seat.agent}"]
    if seat.organizer:
        marks.append("organizer")
    if seat.retired:
        marks.append("retired")
    if seat.scope is not None:
        parts = [
            f"{label} {' and '.join(names)}"
            for label, names in (
                ("workstreams", seat.scope.workstreams),
                ("types", seat.scope.types),
            )
            if names
        ]
        marks.append("scope: " + " with ".join(parts))
    issue = f"#{seat.state_issue}" if seat.state_issue is not None else "no state issue"
    holder = "no state issue named" if seat.state_issue is None else state.said()
    line = f"  {seat.number}. {seat.name} ({', '.join(marks)}), {issue}: {holder}"
    return line + ("  ← this clone" if mine else "")


def stray_state_issues(
    tree: topology.Topology, rows: Iterable[dict[str, Any]]
) -> list[tuple[int, str]]:
    """The open state issues of a seat that no seat of ``tree`` names, by their
    description's marker, in number order.

    Anyone who may open an issue may write such a marker, so a key that is no
    seat's name is shown quoted, with each character a terminal acts on
    escaped."""
    named = {seat.state_issue for seat in tree.seats if seat.state_issue is not None}
    out: list[tuple[int, str]] = []
    for row in rows:
        number = row.get("number")
        if not isinstance(number, int) or number in named:
            continue
        marker = state_issues.read_marker(str(row.get("body") or ""))
        if marker is not None and marker.kind == topology.SEAT_KIND and marker.key:
            key = marker.key
            out.append((number, key if topology.NAME_PATTERN.fullmatch(key) else repr(key)))
    return sorted(out)


def read_members(capability_root: Path) -> list[dict]:
    """The members the working tree holds, as DEC-021's check of who runs a
    command reads them."""
    file = members_path(capability_root)
    try:
        data = YAML(typ="safe").load(file.read_text(encoding="utf-8")) if file.is_file() else None
    except (OSError, YAMLError):
        data = None
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
