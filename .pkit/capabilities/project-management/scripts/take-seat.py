#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — take-seat (DEC-059 point 4).

A clone takes a seat of the project's topology, and then acts as that seat's
instance, under the seat's name, with the seat's number (DEC-059 point 6). The
topology is read from the default branch, at the commit the backbone resolves
it to, and the command says which commit it read (point 1).

- **By name,** `take-seat <name>`, the seat named. Otherwise the first free
  seat in the topology's order, or the first free seat of `--role`.
- **Only a seat of this session's agent definition.** A seat names the agent
  definition its agent follows, the project-manager agent's by default (point
  2). The session says which definition it follows, with `--agent <name>`, or
  with the `PKIT_AGENT` variable of its environment, which a platform that
  starts sessions may set. The command reads no harness's files, and takes no
  seat where neither says.
- **A claim on the seat's state issue** (DEC-058 points 5 and 6), through the
  state-issue seam (`_lib/state_issues`, ADR-071): a read, the claim's comment
  and a read again. The first claim on a free seat holds. The claim names the
  account, the clone's key and where the clone lies, its machine and folder.
  The clone generates its key the first time it takes a seat, and keeps it in
  its git-ignored runtime file, beside the name of the seat it took.
- **One seat for each clone.** A clone that holds a seat takes it up again, as
  a new session in it does, since the key outlives every session (point 4). It
  takes no second seat. A retired seat it holds is released first (point 5).
- **No seat is taken** where the default branch cannot be resolved, where a
  seat names no state issue or its state issue cannot be read (point 3), or
  where another clone holds the seat. A clone that loses the seat to a claim
  made in the same instant holds no seat, and writes nothing more: its agent
  takes another free seat, or stops, as it judges.
- **No seat is taken by code that cannot read the topology in full** (DEC-061
  point 9): a key it does not know, at any depth, or a value it cannot read.
  The refusal says what it did not understand, and exits 2.
- **The pools.** Where the topology declares pools of workers, the command
  shows each pool's open milestones, by number and title, read once, and warns
  of what would leave work stranded: a pool no seat serves, a pool with no open
  milestone, a seat that builds and names no pool, and a milestone whose `Pool:`
  line names an undeclared pool (DEC-061 point 10). Where the milestones cannot
  be read, it says so and still takes the seat (ADR-072 point 6).

Who may write on a seat's state issue comes from the members the default branch
holds (ADR-071 point 3). The membership gate (DEC-021), the bootstrap gate and
the foreign-repo guard run first. Taking a seat is the agent's own step, with
no person's authorisation.

Usage:
  pkit pm take-seat [<name>] [--role planner|worker|lead] [--agent <definition>] [--dry-run]

Exit codes:
  0  this clone holds the seat, taken now or taken up, or a dry run printed its plan
  1  refused: membership, no topology, the default branch, no free seat that
     matches, a seat another clone holds or took first
  2  usage error: the capability is not found or not bootstrapped, or no agent
     definition was given / this code cannot read the topology in full
  3  GitHub failed
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    bootstrap_gate,
    instance_identity,
    pools,
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

VERB = "take-seat"

#: The variable of a session's environment that names the agent definition the
#: session follows, where `--agent` does not.
AGENT_ENV = "PKIT_AGENT"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Take a seat of the topology for this clone: the one named, or the first free "
            "one, of --role where given (DEC-059 point 4)."
        ),
    )
    parser.add_argument("name", nargs="?", default=None, help="The seat to take.")
    parser.add_argument(
        "--role", choices=topology.ROLES, default=None, help="Take the first free seat of it."
    )
    parser.add_argument(
        "--agent",
        default=None,
        help=f"The agent definition this session follows (default: ${AGENT_ENV}).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; claim nothing.")
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
    if not bootstrap_gate.enforce("take-seat", capability_root=capability_root):
        return 2
    agent, problem = session_agent(args.agent, os.environ)
    if agent is None:
        print(f"error: {problem}", file=sys.stderr)
        return 2

    config = load_adopter_config(capability_root)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(read_members(capability_root), invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1
    # The claim and the runtime file are this repository's: refuse a cd into another.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    return take_seat(
        capability_root,
        name=args.name,
        role=args.role,
        agent=agent,
        login=invoker.github_login,
        gh=state_issues.runner(config),
        dry_run=args.dry_run,
    )


def session_agent(
    explicit: str | None, environ: Mapping[str, str]
) -> tuple[str | None, str | None]:
    """The agent definition this session follows: ``--agent``, else the
    session's ``PKIT_AGENT``. Or None, and why, where neither names one."""
    agent = (explicit or environ.get(AGENT_ENV, "")).strip()
    if agent and topology.AGENT_PATTERN.fullmatch(agent):
        return agent, None
    said = f" {agent!r} is no definition's name." if agent else ""
    return None, (
        f"say which agent definition this session follows, with --agent <name> or "
        f"${AGENT_ENV}: a seat is taken only where it names the session's definition "
        f"(DEC-059 point 4).{said}"
    )


def take_seat(
    capability_root: Path,
    *,
    name: str | None,
    role: str | None,
    agent: str,
    login: str | None,
    gh: state_issues.Gh,
    dry_run: bool = False,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
    versions: Any = None,
) -> int:
    """Take the seat ``name``, or the first free one of ``role``, for this clone.

    ``gh`` runs each call of the state-issue seam, ``run`` the backbone's
    reading of the default branch, and ``git`` the reads at its commit. Returns
    the exit code."""
    if not login:
        return _refuse("this clone's GitHub account could not be resolved, so no seat is taken.")
    key = instance_identity.read_clone_key(capability_root)
    try:
        snap = topology.snapshot(
            capability_root, gh=gh, account=login, key=key, run=run, git=git, versions=versions
        )
    except topology.Unresolved as exc:
        return _refuse(
            f"the topology could not be read from the default branch ({exc}), and no seat is "
            "taken without it (DEC-059 point 1)."
        )
    if snap is None:
        return _refuse(
            f"the default branch declares no topology ({topology.TOPOLOGY_RELATIVE}), so there "
            "is no seat to take."
        )
    tree = snap.topology
    print(f"{VERB}: the topology of {tree.where()}")
    for problem in tree.problems:
        print(f"warn: {topology.TOPOLOGY_RELATIVE}: {problem.message}", file=sys.stderr)
    refusal = topology.not_understood_refusal(tree)
    if refusal is not None:
        print(f"[refused] {VERB}: {refusal} No seat is taken.", file=sys.stderr)
        return 2
    show_pools(tree, gh)

    named = tree.seat(name) if name is not None else None
    if name is not None:
        refusal = _named_refusal(name, named, role, agent)
        if refusal is not None:
            return _refuse(refusal)

    held, code = _held_seats(snap, capability_root, dry_run=dry_run)
    if code is not None:
        return code
    if held is not None:
        return _take_up(held, capability_root, name=name, role=role, agent=agent, dry_run=dry_run)

    if named is not None:
        state = snap.state(named.name)
        assert state is not None
        if state.state == topology.UNREAD:
            return _refuse(
                f"the seat {named.name} cannot be taken, since {state.cause} (DEC-059 point 3)."
            )
        if state.state == topology.HELD:
            return _refuse(f"the seat {named.name} is {state.said()}.")
        chosen = state
    else:
        chosen = _first_free(snap, role, agent)
        if chosen is None:
            wanted = f"of the role {role}" if role else "in the topology"
            return _refuse(
                f"no free seat {wanted} names the agent definition {agent}, so this clone "
                "takes no seat, marks no issue and is guarded by nothing (DEC-059 point 6)."
            )

    seat = chosen.seat
    assert seat.state_issue is not None
    if dry_run:
        print(f"  seat {seat.number} ({seat.name}, a {seat.role}): free, on #{seat.state_issue}")
        print("\n[dry-run] nothing claimed, and the runtime file is unchanged.")
        return 0
    clone = state_issues.Clone(
        login, instance_identity.ensure_clone_key(capability_root), snap.clone.place
    )
    outcome = state_issues.claim(seat.state_issue, topology.SEAT_KIND, seat.name, clone, snap.run)
    if outcome.outcome in (state_issues.CLAIMED, state_issues.HELD):
        instance_identity.write_seat_hint(capability_root, seat.name)
        _say_held(seat, "took", outcome.view)
        return 0
    if outcome.outcome in (state_issues.LOST, state_issues.HELD_ELSEWHERE):
        holder = outcome.holder
        who = (
            f"@{topology.shown(holder.account)}, clone {topology.shown(holder.clone)}"
            if holder is not None
            else "another clone"
        )
        return _refuse(
            f"{who} took the seat {seat.name} first, so this clone holds no seat and writes "
            "nothing more (DEC-058 point 6). Take another free seat, or stop."
        )
    if outcome.outcome == state_issues.NO_STATE_ISSUE:
        return _refuse(f"#{seat.state_issue} is no state issue of the seat {seat.name}.")
    print(
        f"[error] the seat {seat.name} could not be claimed on #{seat.state_issue}: "
        f"{outcome.cause or outcome.outcome}",
        file=sys.stderr,
    )
    return 3


def show_pools(tree: topology.Topology, gh: state_issues.Gh) -> None:
    """Where the topology declares pools, show each pool's open milestones, read
    once, and warn of what would leave work stranded (DEC-061 point 10). Where
    the milestones cannot be read, say so and go on: no milestone decides which
    seat a clone takes (ADR-072 point 6)."""
    if tree.pools is None:
        return
    pool_map = pools.read_map(tree.pools, gh=gh)
    if pool_map is None:
        print(
            "warn: the open milestones could not be read, so no pool's milestones are shown.",
            file=sys.stderr,
        )
    else:
        pools.show_pools(pool_map)
    for warning in pools.listing_warnings(tree, pool_map):
        print(f"warn: {warning}", file=sys.stderr)


def _named_refusal(
    name: str, seat: topology.Seat | None, role: str | None, agent: str
) -> str | None:
    """Why the seat named cannot be taken, before any read, or None."""
    if seat is None:
        return f"the topology holds no seat named {name}."
    if seat.retired:
        return f"the seat {name} is retired, and a retired seat is not taken."
    if role is not None and seat.role != role:
        return f"the seat {name} is a {seat.role}'s, not a {role}'s."
    if seat.agent != agent:
        return (
            f"the seat {name} names the agent definition {seat.agent}, and this session "
            f"follows {agent} (DEC-059 point 4)."
        )
    return None


def _held_seats(
    snap: topology.Snapshot, capability_root: Path, *, dry_run: bool
) -> tuple[topology.SeatState | None, int | None]:
    """The seat this clone already holds, after releasing each retired one it
    holds; or the exit code where the reading stops the run.

    Every seat that names a state issue is read, so a clone takes no second seat
    whatever its runtime file says. A clone with no key holds none."""
    if not snap.clone.key:
        return None, None
    states = snap.states()
    hint = instance_identity.read_seat_hint(capability_root)
    for state in states:
        if state.state != topology.UNREAD:
            continue
        if state.seat.name == hint:
            print(
                f"[error] the seat this clone took, {hint}, could not be read, since "
                f"{state.cause}. Run this again once it can be.",
                file=sys.stderr,
            )
            return None, 3
        if not state.seat.retired:
            _warn_unread(state)
    held = [s for s in states if s.held_by(snap.clone)]
    for state in [s for s in held if s.seat.retired]:
        if not _release_retired(snap, state, capability_root, dry_run=dry_run):
            return None, 3
    active = [s for s in held if not s.seat.retired]
    return (active[0] if active else None), None


def _release_retired(
    snap: topology.Snapshot, state: topology.SeatState, capability_root: Path, *, dry_run: bool
) -> bool:
    """Release a retired seat this clone holds (DEC-059 point 5). False where
    the release failed."""
    seat = state.seat
    assert seat.state_issue is not None
    if dry_run:
        print(f"  the seat {seat.name} is retired, and this clone holds it: it would be released")
        return True
    released = state_issues.release(
        seat.state_issue, topology.SEAT_KIND, seat.name, snap.clone, snap.run
    )
    if released.outcome in (state_issues.RELEASED, state_issues.NOTHING, state_issues.NOT_HOLDER):
        snap.learn(seat, released.read)
        if instance_identity.read_seat_hint(capability_root) == seat.name:
            instance_identity.clear_seat_hint(capability_root)
        print(f"  released the retired seat {seat.name} on #{seat.state_issue}")
        return True
    print(
        f"[error] the retired seat {seat.name} could not be released on #{seat.state_issue}: "
        f"{released.cause or released.outcome}",
        file=sys.stderr,
    )
    return False


def _take_up(
    held: topology.SeatState,
    capability_root: Path,
    *,
    name: str | None,
    role: str | None,
    agent: str,
    dry_run: bool,
) -> int:
    """Take up the seat this clone holds, as a new session in it does (DEC-059
    point 4), where it is the seat asked for."""
    seat = held.seat
    release = f"Release it first (`pkit pm release-seat {seat.name}`)."
    if name is not None and name != seat.name:
        return _refuse(
            f"this clone holds the seat {seat.name}, and a clone holds at most one seat. {release}"
        )
    if role is not None and seat.role != role:
        return _refuse(
            f"this clone holds the seat {seat.name}, a {seat.role}'s, and a clone holds at most "
            f"one seat. {release}"
        )
    if seat.agent != agent:
        return _refuse(
            f"this clone holds the seat {seat.name}, which names the agent definition "
            f"{seat.agent}, and this session follows {agent}. Start the session with that "
            f"definition, or {release[0].lower()}{release[1:]}"
        )
    if dry_run:
        print(f"  this clone holds the seat {seat.name}, and takes it up")
        print("\n[dry-run] nothing claimed, and the runtime file is unchanged.")
        return 0
    instance_identity.write_seat_hint(capability_root, seat.name)
    _say_held(seat, "takes up", None)
    return 0


def _first_free(snap: topology.Snapshot, role: str | None, agent: str) -> topology.SeatState | None:
    """The first free seat, in the topology's order, of ``role`` where given,
    that names ``agent`` and names its state issue."""
    warned = bool(snap.clone.key)  # the reading of every seat warned already
    for seat in snap.topology.active:
        if (role is not None and seat.role != role) or seat.agent != agent:
            continue
        state = snap.state(seat.name)
        if state is not None and state.state == topology.FREE:
            return state
        if state is not None and state.state == topology.UNREAD and not warned:
            _warn_unread(state)
    return None


def _warn_unread(state: topology.SeatState) -> None:
    print(
        f"warn: the seat {state.seat.name} cannot be taken, since {state.cause}.", file=sys.stderr
    )


def _say_held(seat: topology.Seat, verb: str, view: str | None) -> None:
    print(
        f"[ok] this clone {verb} the seat {seat.name}, on #{seat.state_issue}. It is now "
        f"instance {seat.number}, named {seat.name} (DEC-059 point 6)."
    )
    print(f"  role:             {seat.role}")
    print(f"  agent definition: {seat.agent}")
    if view == state_issues.FAILED:
        print(
            f"warn: the state issue #{seat.state_issue}'s description could not be rewritten; "
            "its comments hold who holds the seat.",
            file=sys.stderr,
        )


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
