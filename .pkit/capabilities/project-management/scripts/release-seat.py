#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — release-seat (DEC-059 point 5).

A seat stays taken until it is released, in the tolerant mode, the only one
built: no seat is freed for its clone's silence.

- **By its clone.** `release-seat`, or `release-seat <name>` naming the seat
  this clone holds, releases it on the seat's state issue, through the
  state-issue seam (`_lib/state_issues`, ADR-071). Every seat that names a state
  issue is read, so the clone finds its seat whatever its runtime file says.
  The clone then forgets the seat, and holds none.
- **By force.** `release-seat <name> --force --reason "<why>"` frees the seat
  whoever holds it, and the seat's state issue logs the reason. It comes from
  the clone of the organizer seat, which the reviewed topology grants it, or
  from a person in any clone. A person authorises it as a held move: at a
  terminal, or with `--yes`, which an agent never passes for itself (DEC-006).
  Off a terminal without `--yes`, a clone that does not hold the organizer seat
  refuses.
- **What a release frees.** A claim on an issue counts only while the clone that
  made it holds the claim's seat (DEC-059 point 9). So a release frees every
  claim of the seat's clone, with no write to those issues.

Who may write on a seat's state issue comes from the members the default branch
holds (ADR-071 point 3). The membership gate (DEC-021), the bootstrap gate and
the foreign-repo guard run first.

Usage:
  pkit pm release-seat [<name>] [--dry-run]
  pkit pm release-seat <name> --force --reason "<why>" [--yes] [--dry-run]

Exit codes:
  0  released, nothing to release, or a dry run printed its plan
  1  refused: membership, no topology, the default branch, a seat this clone does
     not hold, or a release by force with no reason or no authorisation
  2  usage error: the capability is not found or not bootstrapped, or --force
     names no seat
  3  GitHub failed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    bootstrap_gate,
    consent,
    instance_identity,
    session_guard,
    state_issues,
    topology,
)
from _lib.gh import load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    members_path,
    resolve_capability_root,
    resolve_invoker_identity,
)

VERB = "release-seat"

#: What a release frees, for the line that reports one.
FREES = (
    "Each claim its clone made as that seat stops counting, with no write to those issues "
    "(DEC-059 point 5)."
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Release this clone's seat, or a seat by force with its reason (DEC-059 point 5)."
        ),
    )
    parser.add_argument("name", nargs="?", default=None, help="The seat to release.")
    parser.add_argument(
        "--force", action="store_true", help="Release the seat whoever holds it, with --reason."
    )
    parser.add_argument("--reason", default=None, help="Why the seat is released by force.")
    parser.add_argument("--yes", action="store_true", help="A person authorises the force.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; write nothing.")
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
    if not bootstrap_gate.enforce(VERB, capability_root=capability_root):
        return 2
    if args.force and not args.name:
        print("error: --force names the seat it releases.", file=sys.stderr)
        return 2
    if args.reason is not None and not args.force:
        print("error: --reason goes with --force.", file=sys.stderr)
        return 2

    config = load_adopter_config(capability_root)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(read_members(capability_root), invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1
    # The release and the runtime file are this repository's: refuse a cd into another.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    gh = state_issues.runner(config)
    if args.force:
        return release_by_force(
            capability_root,
            name=args.name,
            reason=args.reason or "",
            login=invoker.github_login,
            gh=gh,
            yes=args.yes,
            dry_run=args.dry_run,
        )
    return release_own(
        capability_root, name=args.name, login=invoker.github_login, gh=gh, dry_run=args.dry_run
    )


def _snapshot(
    capability_root: Path,
    login: str | None,
    gh: state_issues.Gh,
    run: Callable[..., Any],
    git: topology.Git | None,
    versions: Any,
) -> tuple[topology.Snapshot | None, int | None]:
    """This run's snapshot, or the exit code that ends the run."""
    if not login:
        return None, _refuse("this clone's GitHub account could not be resolved.")
    key = instance_identity.read_clone_key(capability_root)
    try:
        snap = topology.snapshot(
            capability_root, gh=gh, account=login, key=key, run=run, git=git, versions=versions
        )
    except topology.Unresolved as exc:
        return None, _refuse(f"the topology could not be read from the default branch ({exc}).")
    if snap is None:
        print(f"{VERB}: the default branch declares no topology, so there is no seat to release.")
        return None, 0
    print(f"{VERB}: the topology of {snap.topology.where()}")
    return snap, None


def release_own(
    capability_root: Path,
    *,
    name: str | None,
    login: str | None,
    gh: state_issues.Gh,
    dry_run: bool = False,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
    versions: Any = None,
) -> int:
    """Release the seat this clone holds, ``name`` where given. Returns the exit code."""
    snap, code = _snapshot(capability_root, login, gh, run, git, versions)
    if snap is None:
        return code if code is not None else 0
    if name is not None and snap.topology.seat(name) is None:
        return _refuse(f"the topology holds no seat named {name}.")
    states = snap.states() if snap.clone.key else ()
    unread = [s for s in states if s.state == topology.UNREAD and s.seat.state_issue is not None]
    held = [s for s in states if s.held_by(snap.clone)]
    if name is not None:
        mine = [s for s in held if s.seat.name == name]
        if not mine:
            state = snap.state(name)
            said = state.said() if state is not None else "not read"
            return _refuse(
                f"this clone does not hold the seat {name}, which is {said}. A seat another "
                f'clone holds is released by force: --force --reason "<why>".'
            )
        held = mine
    if not held:
        for state in unread:
            print(
                f"warn: the seat {state.seat.name} could not be read: {state.cause}.",
                file=sys.stderr,
            )
        if unread:
            print(
                "[error] a seat that could not be read may be this clone's, so nothing was "
                "released. Run this again once each can be read.",
                file=sys.stderr,
            )
            return 3
        forgot = not dry_run and instance_identity.clear_seat_hint(capability_root)
        print(f"[ok] this clone holds no seat{', and forgot the one it took' if forgot else ''}.")
        return 0
    code = 0
    for state in held:
        seat = state.seat
        assert seat.state_issue is not None
        if dry_run:
            print(f"  seat {seat.name}, on #{seat.state_issue}: would be released")
            continue
        released = state_issues.release(
            seat.state_issue, topology.SEAT_KIND, seat.name, snap.clone, snap.run
        )
        if released.outcome in (
            state_issues.RELEASED,
            state_issues.NOTHING,
            state_issues.NOT_HOLDER,
        ):
            _forget(capability_root, seat.name)
            print(f"[ok] released the seat {seat.name}, on #{seat.state_issue}. {FREES}")
            continue
        print(
            f"[error] the seat {seat.name} could not be released on #{seat.state_issue}: "
            f"{released.cause or released.outcome}",
            file=sys.stderr,
        )
        code = 3
    if dry_run:
        print("\n[dry-run] nothing released, and the runtime file is unchanged.")
    return code


def release_by_force(
    capability_root: Path,
    *,
    name: str,
    reason: str,
    login: str | None,
    gh: state_issues.Gh,
    yes: bool = False,
    dry_run: bool = False,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
    versions: Any = None,
) -> int:
    """Release the seat ``name`` by force, with ``reason``, from the organizer
    seat's clone or on a person's authorisation. Returns the exit code."""
    if not reason.strip():
        return _refuse(
            "a release by force carries its reason, which the seat's state issue logs: "
            '--reason "<why>".'
        )
    snap, code = _snapshot(capability_root, login, gh, run, git, versions)
    if snap is None:
        return code if code is not None else 0
    target = snap.topology.seat(name)
    if target is None:
        return _refuse(f"the topology holds no seat named {name}.")
    if target.state_issue is None:
        return _refuse(f"the seat {name} names no state issue, so no clone holds it.")
    state = snap.state(name)
    assert state is not None
    if state.state == topology.UNREAD:
        print(f"[error] the seat {name} could not be read: {state.cause}.", file=sys.stderr)
        return 3
    if state.state == topology.FREE:
        print(f"[ok] the seat {name} is free, so there is nothing to release.")
        return 0
    organizer = _as_organizer(snap)
    print(f"  seat {name}, on #{target.state_issue}: {state.said()}")
    print(f"  reason: {reason.strip()}")
    if organizer is not None:
        print(f"  by: this clone, which holds the organizer seat {organizer}")
    else:
        print("  by: a person, since this clone does not hold the organizer seat")
    if dry_run:
        print("\n[dry-run] nothing released.")
        return 0
    if organizer is None:
        stop = consent.authorise(
            f"Release the seat {name} by force? [y/N] ",
            yes=yes,
            step=f"Releasing the seat {name} by force",
            verb=VERB,
        )
        if stop is not None:
            return stop
    clone = state_issues.Clone(
        login or "", instance_identity.ensure_clone_key(capability_root), snap.clone.place
    )
    released = state_issues.force_release(
        target.state_issue, topology.SEAT_KIND, name, clone, reason, snap.run
    )
    if released.outcome == state_issues.RELEASED:
        freed = released.freed
        who = f"@{freed.account}, clone {freed.clone}" if freed is not None else "its holder"
        if freed is not None and freed.is_clone(clone.account, clone.key):
            _forget(capability_root, name)
        print(
            f"[ok] released the seat {name} by force, on #{target.state_issue}, from {who}. "
            f"The reason is on the state issue. {FREES}"
        )
        return 0
    if released.outcome == state_issues.NOTHING:
        print(f"[ok] the seat {name} was free when the release landed, so nothing was released.")
        return 0
    print(
        f"[error] the seat {name} could not be released on #{target.state_issue}: "
        f"{released.cause or released.outcome}",
        file=sys.stderr,
    )
    return 3


def _as_organizer(snap: topology.Snapshot) -> str | None:
    """The organizer seat's name, where this clone holds it, confirmed on its
    state issue; else None (DEC-059 point 5)."""
    organizer = snap.topology.organizer
    if organizer is None or not snap.clone.key:
        return None
    state = snap.state(organizer.name)
    return organizer.name if state is not None and state.held_by(snap.clone) else None


def _forget(capability_root: Path, name: str) -> None:
    if instance_identity.read_seat_hint(capability_root) == name:
        instance_identity.clear_seat_hint(capability_root)


def _refuse(why: str) -> int:
    print(f"[refused] {VERB}: {why}", file=sys.stderr)
    return 1


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
