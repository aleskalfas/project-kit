#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — check-message (DEC-084 points 2 and 4).

Says whether a message this session received is a directive, information, or
cannot be checked, with why. The session's agent feeds it what the message
carries, as one JSON object on standard input:

    {"reply_address": "<as the message carries it>",
     "sender_name": "<the name it came under>",
     "seat": "<the seat it names as the one it is meant for>"}

Each is a string, or null or left out where the message carries none.

The command reads the rest itself (DEC-084 point 2), and the listing of
sessions takes no part:

- **The seat this clone holds,** the one it took (its runtime file names it),
  from the topology the default branch holds (DEC-059 point 1) and the seat's
  state issue, with the session it records (`_lib/state_issues`).
- **Whom the message must come from.** For a worker's seat, the seat that
  directs it (DEC-081 point 3). For a directing seat, the seat of the workers
  it directs whose record holds the message's sender name: a report (DEC-084
  point 4).
- **This session's facts,** from the backbone (`_lib/processes`): its messaging
  address, whether its harness gives messaging, and the message's reply address
  in the address's form. And the machine it runs on.
- **Whether the sender's recorded process runs,** as the backbone reads it from
  here (ADR-103).

One pure check judges them (`_lib/seat_sessions`). A message is a directive, or
for a directing seat a worker's report, only where every condition holds. Where
anything it needs cannot be read, the verdict is that it cannot be checked, and
the tracker carries the work (DEC-081 point 1). Like the guard on a claim, it
catches the mistakes of sessions that follow the procedure, and stops no one who
means to pass as another (DEC-084 point 5).

It prints one line, `[directive]`, `[information]` or `[cannot-check]`, and
why. A read of a state issue restores a marker a hand removed from its
description (ADR-071 point 5), so the foreign-repo guard runs first, after the
membership gate (DEC-021) and the bootstrap gate.

Usage:
  pkit pm check-message < message.json

Exit codes:
  0  a verdict was printed
  1  refused: membership
  2  usage error: the capability is not found or not bootstrapped, or the
     request is not one JSON object of strings
"""

from __future__ import annotations

import argparse
import json
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
    members_path,
    resolve_capability_root,
    resolve_invoker_identity,
)

VERB = "check-message"

#: The keys a request may hold, each a string or null.
KEYS = ("reply_address", "sender_name", "seat")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Say whether a message, given as JSON on standard input, is a directive, "
            "information, or cannot be checked (DEC-084 points 2 and 4)."
        ),
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
    if not bootstrap_gate.enforce("check-message", capability_root=capability_root):
        return 2
    message, problem = read_message(sys.stdin.read())
    if message is None:
        print(f"error: {problem}", file=sys.stderr)
        return 2

    config = load_adopter_config(capability_root)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(read_members(capability_root), invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1
    # A read of a state issue may restore its marker: refuse a cd into another repository.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1
    verdict = judge(
        capability_root,
        message,
        login=invoker.github_login,
        gh=state_issues.runner(config),
    )
    print(f"[{verdict.outcome}] {VERB}: {verdict.why}.")
    return 0


def read_message(text: str) -> tuple[Mapping[str, str | None] | None, str | None]:
    """The message a request holds, by ``KEYS``, or None and why where the
    request is no JSON object whose values at those keys are strings or null."""
    try:
        request: object = json.loads(text)
    except ValueError as exc:
        return None, f"the request on standard input is no JSON: {exc}"
    if not isinstance(request, dict):
        return None, "the request on standard input is no JSON object"
    found: dict[str, str | None] = {}
    for key in KEYS:
        value = request.get(key)
        if value is not None and not isinstance(value, str):
            return None, f"`{key}` is neither a string nor null"
        found[key] = value or None
    return found, None


def judge(
    capability_root: Path,
    message: Mapping[str, str | None],
    *,
    login: str | None,
    gh: state_issues.Gh,
    run: Callable[..., Any] = subprocess.run,
    git: topology.Git | None = None,
    versions: Any = None,
    processes_run: processes.Runner | None = None,
) -> seat_sessions.Verdict:
    """The verdict on ``message`` for the session this command runs in.

    ``gh`` runs each call of the state-issue seam, ``run`` the backbone's
    reading of the default branch, ``git`` the reads at its commit, and
    ``processes_run`` the backbone's readings of sessions and processes."""

    def cannot(why: str) -> seat_sessions.Verdict:
        return seat_sessions.Verdict(seat_sessions.CANNOT_CHECK, why)

    key = instance_identity.read_clone_key(capability_root)
    try:
        snap = topology.snapshot(
            capability_root, gh=gh, account=login, key=key, run=run, git=git, versions=versions
        )
    except topology.Unresolved as exc:
        return cannot(f"the topology could not be read from the default branch ({exc})")
    if snap is None:
        return cannot("the default branch declares no topology")
    hint = instance_identity.read_seat_hint(capability_root)
    own = snap.state(hint) if hint is not None else None
    if own is not None and own.state == topology.UNREAD:
        return cannot(
            f"the state issue of the seat {own.seat.name} could not be read ({own.cause})"
        )
    if own is None or not own.held_by(snap.clone) or own.seat.retired:
        return cannot("this clone holds no seat it took")
    sender = _sender(snap, own.seat, message.get("sender_name"))
    if isinstance(sender, seat_sessions.Verdict):
        return sender

    given = message.get("reply_address")
    session = processes.session([given] if given else [], run=processes_run)
    if not session.found:
        return cannot(f"this command runs in no harness session it can read ({session.why})")
    reply = session.replies[0] if session.replies else None
    theirs = sender.record
    sender_process = None
    if theirs is not None and theirs.process is not None:
        (sender_process,) = processes.read([theirs.process], run=processes_run)
    return seat_sessions.check(
        seat_sessions.Message(
            reply_address=reply.address if reply is not None else None,
            sender_name=message.get("sender_name"),
            seat=message.get("seat"),
            reply_why=reply.why if reply is not None and reply.address is None else None,
        ),
        own=seat_sessions.Side(own.seat.name, True, own.session),
        own_address=session.address,
        machine=topology.machine(),
        sender=sender,
        sender_process=sender_process,
        messaging=session.messaging,
    )


def _sender(
    snap: topology.Snapshot, seat: topology.Seat, sender_name: str | None
) -> seat_sessions.Side | seat_sessions.Verdict:
    """The side a message to ``seat`` must come from: a worker's directing seat,
    or for a directing seat the worker whose record holds the sender's name. A
    Verdict where a seat it needs could not be read."""
    tree = snap.topology
    if seat.role == topology.WORKER:
        directing = tree.directing(seat)
        if directing is None:
            return seat_sessions.Side(None, False, None)
        return _side(snap, directing) or _unread(directing.name)
    sides: list[seat_sessions.Side] = []
    unread: list[str] = []
    for worker in tree.directed(seat):
        side = _side(snap, worker)
        if side is None:
            unread.append(worker.name)
        else:
            sides.append(side)
    found = seat_sessions.report_sender(sides, sender_name)
    if unread and isinstance(found, seat_sessions.Verdict):
        return _unread(", ".join(unread))
    return found


def _side(snap: topology.Snapshot, seat: topology.Seat) -> seat_sessions.Side | None:
    """``seat``'s side: whether a clone holds it, and the session it records. None
    where its state issue could not be read."""
    state = snap.state(seat.name)
    if state is None or state.state == topology.UNREAD:
        return None
    return seat_sessions.Side(seat.name, state.state == topology.HELD, state.session)


def _unread(seats: str) -> seat_sessions.Verdict:
    return seat_sessions.Verdict(
        seat_sessions.CANNOT_CHECK, f"the state issue of the seat {seats} could not be read"
    )


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
