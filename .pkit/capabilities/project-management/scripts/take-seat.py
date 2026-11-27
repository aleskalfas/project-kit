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

- **A take for the seat's loop** (`--loop`) records the session that runs the
  loop on the seat's state issue, once the clone holds the seat (DEC-081 point
  4, DEC-084 points 1 and 3): its name, given by `--session-name` or the
  `PKIT_SESSION_NAME` variable, its machine, and the messaging address and the
  process the backbone gives for the harness session whose shell runs the
  command (`_lib/processes`). It records without asking where the seat records
  no session, the recorded process has ended, or it is this session's own, as
  the backbone tells. Otherwise only on the person's word, given in this
  session: at a terminal, or with `--yes`. Without it the loop runs
  unrecorded, and is told so. A record that already holds the session posts
  nothing. A session whose address the backbone does not give records its name
  and machine only, and no message to or from it counts as a directive. A take
  without `--loop` records nothing.

- **Under a credential that names no user's account** (DEC-076 point 6), such
  as an App installation's token, the clone takes no seat that builds, a
  worker's or a lead's, since none of its claims on a Task would count. It
  takes a planner's seat, the organizer seat among them where it is a
  planner's, only where the members the default branch holds close the gate
  and its own account is a member, which it reads before it claims. Where the
  gate is open, or where GitHub gives no answer for the credential, it takes
  no seat.

Who may write on a seat's state issue comes from the members the default branch
holds (ADR-071 point 3). The membership gate (DEC-021), the bootstrap gate and
the foreign-repo guard run first. Taking a seat is the agent's own step, with
no person's authorisation.

Usage:
  pkit pm take-seat [<name>] [--role planner|worker|lead] [--agent <definition>]
                    [--loop --session-name <name> [--yes]] [--dry-run]

Exit codes:
  0  this clone holds the seat, taken now or taken up, or a dry run printed its
     plan; with --loop, its session recorded, already recorded, or left
     unrecorded without the person's word
  1  refused: membership, no topology, the default branch, no free seat that
     matches, a seat another clone holds or took first, a seat that builds or
     an open gate under a credential that names no user's account (DEC-076
     point 6); with --loop, the seat no longer this clone's, or another of its
     sessions recorded after this one
  2  usage error: the capability is not found or not bootstrapped, no agent
     definition was given, --loop with no session name / this code cannot read
     the topology in full
  3  GitHub failed, or the session's record could not be written (the seat is
     held)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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
    pools,
    processes,
    seat_sessions,
    session_guard,
    state_issues,
    topology,
)
from _lib.gh import load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    format_unresolved,
    members_path,
    resolve_capability_root,
    resolve_invoker_identity,
)

VERB = "take-seat"

#: The variable of a session's environment that names the agent definition the
#: session follows, where `--agent` does not.
AGENT_ENV = "PKIT_AGENT"

#: The variable that names the session a take for the loop records, where
#: `--session-name` does not: the name the harness puts on its messages.
SESSION_NAME_ENV = "PKIT_SESSION_NAME"

#: The longest session name recorded, so the seat's record stays one line.
SESSION_NAME_LIMIT = 100


@dataclass(frozen=True)
class Loop:
    """A take for the seat's loop: the session's name, and whether the person
    gave their word, with `--yes`, to record it over another (DEC-084 point 3)."""

    name: str
    yes: bool = False


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
    parser.add_argument(
        "--loop",
        action="store_true",
        help="This session runs the seat's loop: record it on the seat's state issue.",
    )
    parser.add_argument(
        "--session-name",
        default=None,
        help=f"With --loop, the name this session's messages carry (default: ${SESSION_NAME_ENV}).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "With --loop, the person's word, given in this session, to record it over "
            "another live session or one no one can tell of (DEC-084 point 3)."
        ),
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
    loop: Loop | None = None
    if args.loop:
        name, problem = session_name(args.session_name, os.environ)
        if name is None:
            print(f"error: {problem}", file=sys.stderr)
            return 2
        loop = Loop(name, yes=args.yes)

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
        login_cause=invoker.unresolved_cause,
        gh=state_issues.runner(config),
        dry_run=args.dry_run,
        names_user=invoker.names_user,
        loop=loop,
    )


def session_name(explicit: str | None, environ: Mapping[str, str]) -> tuple[str | None, str | None]:
    """The name a take for the loop records: ``--session-name``, else the
    session's ``PKIT_SESSION_NAME``. Or None, and why, where neither names one
    or the name is not one line of at most ``SESSION_NAME_LIMIT`` characters."""
    name = (explicit or environ.get(SESSION_NAME_ENV, "")).strip()
    if not name:
        return None, (
            f"say which name this session's messages carry, with --session-name <name> or "
            f"${SESSION_NAME_ENV}: a take for the loop records it (DEC-081 point 4)."
        )
    if len(name) > SESSION_NAME_LIMIT or not name.isprintable():
        return None, (
            f"the session name {topology.shown(name[:SESSION_NAME_LIMIT])!r} is not one line "
            f"of at most {SESSION_NAME_LIMIT} characters."
        )
    return name, None


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
    login_cause: str | None = None,
    dry_run: bool = False,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
    versions: Any = None,
    names_user: bool = True,
    loop: Loop | None = None,
    processes_run: processes.Runner | None = None,
) -> int:
    """Take the seat ``name``, or the first free one of ``role``, for this clone.

    ``login`` is the account acting, and ``login_cause`` why it could not be
    resolved, where it could not (#3162). ``gh`` runs each call of the
    state-issue seam, ``run`` the backbone's reading of the default branch, and
    ``git`` the reads at its commit. ``names_user`` is whether GitHub answered
    that the credential acts as a user's account: where it did not, only a
    planner's seat is taken, behind a closed gate whose members name the
    clone's own account (DEC-076 point 6). ``loop``, where given, is a take for
    the seat's loop, whose session is recorded once the clone holds the seat,
    and ``processes_run`` runs the backbone's readings of it. Returns the exit
    code."""
    if not login:
        return _refuse(f"{format_unresolved(login_cause)}, so no seat is taken.")
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
    if not names_user:
        refusal = _no_user_refusal(snap, login, named, role)
        if refusal is not None:
            return _refuse(refusal)
        role = topology.PLANNER

    held, code = _held_seats(snap, capability_root, dry_run=dry_run)
    if code is not None:
        return code
    if held is not None:
        code = _take_up(held, capability_root, name=name, role=role, agent=agent, dry_run=dry_run)
        if code != 0 or loop is None:
            return code
        if dry_run:
            print("[dry-run] no session is recorded.")
            return code
        return record_loop(held.seat, held.session, snap.clone, snap.run, loop, run=processes_run)

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
        if loop is not None:
            print("[dry-run] no session is recorded.")
        return 0
    clone = state_issues.Clone(
        login, instance_identity.ensure_clone_key(capability_root), snap.clone.place
    )
    outcome = state_issues.claim(seat.state_issue, topology.SEAT_KIND, seat.name, clone, snap.run)
    if outcome.outcome in (state_issues.CLAIMED, state_issues.HELD):
        instance_identity.write_seat_hint(capability_root, seat.name)
        _say_held(seat, "took", outcome.view)
        if loop is None:
            return 0
        found = outcome.read.fold if outcome.read is not None else None
        recorded = found.session if found is not None else None
        return record_loop(seat, recorded, clone, snap.run, loop, run=processes_run)
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


def record_loop(
    seat: topology.Seat,
    record: state_issues.Session | None,
    clone: state_issues.Clone,
    state_run: state_issues.StateRun,
    loop: Loop,
    *,
    run: processes.Runner | None = None,
) -> int:
    """Record the session that runs the seat's loop, over ``record``, the one the
    seat's state issue holds, as DEC-084 point 3's one rule says (DEC-081 point
    4), under the claim of ``clone``, which holds the seat. The session's
    address and process come from the backbone, which also reads whether the
    recorded process runs and whether it is this session's. Returns the exit
    code."""
    assert seat.state_issue is not None
    session = processes.session(run=run)
    own = state_issues.Session(loop.name, topology.machine(), session.address, session.process)
    if session.address is None:
        why = session.address_why or session.process_why or session.why or "it is not given"
        print(
            f"warn: this session's messaging address is not read ({why}), so the seat's record "
            "holds its name and machine only, and no message to or from it counts as a "
            "directive (DEC-084 point 1).",
            file=sys.stderr,
        )
    recorded: processes.Reading | None = None
    same: str | None = None
    if record is not None and record.process is not None and record != own:
        (recorded,) = processes.read([record.process], run=run)
        if own.process is not None:
            same = processes.compare(record.process, own.process, run=run)
    decision = seat_sessions.recording(record, own, recorded=recorded, same=same)
    if decision.action == seat_sessions.ALREADY:
        print(f"  session:          {_session_line(own)}, already recorded")
        return 0
    if decision.action == seat_sessions.ASK:
        print(f"{VERB}: {decision.why}.")
        stop = consent.authorise(
            f"Record this session, {topology.shown(own.name)}, in its place? [y/N] ",
            yes=loop.yes,
            step=f"Recording this session over the one the seat {seat.name} records",
            verb=VERB,
        )
        if stop is not None:
            print(
                "[unrecorded] this loop runs unrecorded: it takes its work from the tracker, "
                "counts no message as a directive and sends none, and applies the rule again "
                "at its next round (DEC-084 point 3)."
            )
            return 0
    outcome = state_issues.record_session(
        seat.state_issue, topology.SEAT_KIND, seat.name, clone, own, state_run
    )
    if outcome.outcome in (state_issues.RECORDED, state_issues.UNCHANGED):
        print(f"  session:          {_session_line(own)}, recorded on #{seat.state_issue}")
        return 0
    if outcome.outcome == state_issues.NOT_HOLDER:
        return _refuse(
            f"the seat {seat.name} is no longer this clone's, so its session is not recorded."
        )
    if outcome.outcome == state_issues.LOST:
        return _refuse(
            f"another session recorded itself on the seat {seat.name} after this one, and which "
            "of two live loops keeps the seat is the person's to settle (DEC-081 point 4)."
        )
    print(
        f"[error] the session could not be recorded on #{seat.state_issue}: "
        f"{outcome.cause or outcome.outcome}. The seat is held; run this again.",
        file=sys.stderr,
    )
    return 3


def _session_line(session: state_issues.Session) -> str:
    shown = topology.shown
    address = shown(session.address) if session.address else "no messaging address"
    return f"{shown(session.name)} on {shown(session.machine)}, {address}"


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


def _no_user_refusal(
    snap: topology.Snapshot, login: str, named: topology.Seat | None, role: str | None
) -> str | None:
    """Why a clone under a credential that names no user's account takes no
    seat here, or None where it may take a planner's (DEC-076 point 6).

    Its claim on the seat's state issue counts, for every reader alike, only as
    a member's, so the gate the default branch's members close is read before
    it claims, by the test the state-issue seam reads its claim by."""
    builds = named.role if named is not None else role
    if builds in topology.BUILDERS:
        return (
            f"GitHub answers that the credential acts as {login}, a bot's account, and a "
            f"clone under a credential that names no user's account takes no {builds}'s seat, "
            "since none of its claims on a Task would count (DEC-076 point 6)."
        )
    if snap.run.writers.gate_open:
        return (
            f"GitHub answers that the credential acts as {login}, a bot's account, and the "
            "members the default branch holds leave the membership gate open, so this clone "
            "takes no seat: a planner's seat is taken under such a credential only behind a "
            "closed gate whose members name its own account (DEC-076 point 6)."
        )
    member, cause = snap.run.may_write(login)
    if member is not True:
        why = f": {cause}" if cause else ""
        return (
            f"GitHub answers that the credential acts as {login}, a bot's account, and no "
            f"member the default branch holds names it{why}, so this clone takes no seat "
            "(DEC-076 point 6)."
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
