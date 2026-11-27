"""The sessions that run seats' loops: when a loop records itself, and whether a
message is a directive (DEC-081, DEC-084).

[project-management:DEC-081-delegation-between-seats] lets a worker's directing
seat message it, to wake it or to name a ready Task it may take next.
[project-management:DEC-084-seat-session-address] decides how a worker tells a
directive from information: each seat's state issue records the session that
runs its loop, by its name, machine, messaging address and process
(``_lib/state_issues``), and a message counts only where it comes from the
directing seat's recorded session to the worker's own.

This module holds the two judgements DEC-084 makes, as pure functions, so both
sides of a seat's messages use one copy of each and the commands only feed
them:

* :func:`recording` says whether a loop records itself without asking, only on
  the person's word, or not at all, since its record already holds it (DEC-084
  point 3);
* :func:`check` says whether a message is a directive, information, or cannot
  be checked, with why (DEC-084 points 2 and 4), and :func:`report_sender`
  which of the seats a directing seat directs a report comes from.

It reads nothing and runs nothing: no ``gh`` call, no process, no file and no
harness. Whether a recorded process runs, and whether two process names name
one process, the backbone answers ([pkit:ADR-103]), and a caller passes its
answers in, read through ``_lib/processes``, with the state issues and its own
session's facts.

Like the guard on a claim (DEC-035 point 6), the check catches the mistakes of
sessions that follow the procedure, and stops no one who means to pass as
another (DEC-084 point 5).
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from _lib.processes import ENDED, ONE, RUNNING, Reading
    from _lib.state_issues import Session
except ImportError:  # pragma: no cover - a test that puts `_lib` itself on the path
    from processes import ENDED, ONE, RUNNING, Reading  # type: ignore[no-redef]
    from state_issues import Session  # type: ignore[no-redef]


# ---- when a loop records itself (DEC-084 point 3) --------------------------------

#: What a loop does with its own session at a take or a round.
RECORD = "record"
ASK = "ask"
ALREADY = "already"


@dataclass(frozen=True)
class Recording:
    """RECORD without asking, ASK the person first, or ALREADY recorded, and why."""

    action: str
    why: str


def recording(
    record: Session | None, own: Session, *, recorded: Reading | None, same: str | None
) -> Recording:
    """Whether a loop records ``own``, its session, over ``record``, its seat's
    record. ``recorded`` is the backbone's reading of the recorded process, and
    ``same`` its answer to whether the recorded process and the loop's own are
    one, each None where it was not asked.

    ALREADY where the record holds ``own`` whole, so nothing is posted. RECORD
    without asking where the record holds no session, the recorded process is
    the loop's own, or it has ended. ASK otherwise: the record is another live
    session's, or one no one can tell of, and only the person's word, given in
    the loop's own session, replaces it.
    """
    if record is None:
        return Recording(RECORD, "the seat records no session")
    if record == own:
        return Recording(ALREADY, "the seat already records this session")
    if same == ONE:
        return Recording(RECORD, "the recorded process is this session's own")
    if recorded is not None and recorded.state == ENDED:
        return Recording(RECORD, f"the recorded session's process has ended: {recorded.why}")
    if recorded is not None and recorded.state == RUNNING:
        return Recording(
            ASK, f"the seat records another live session, {record.name}: {recorded.why}"
        )
    why = recorded.why if recorded is not None else "its process was not read"
    return Recording(
        ASK,
        f"no one can tell whether the recorded session {record.name} still runs: {why}",
    )


# ---- whether a message is a directive (DEC-084 points 2 and 4) ------------------

#: What a message is to the session that takes it.
DIRECTIVE = "directive"
INFORMATION = "information"
CANNOT_CHECK = "cannot-check"


@dataclass(frozen=True)
class Message:
    """What the check reads of a message: its reply address, in the form the
    adapter's declaration gives, the sender's name, and the seat it names as the
    one it is meant for. Each is None where the message carries none.
    ``reply_why`` says why a reply address the message carries could not be
    brought into that form, where it could not."""

    reply_address: str | None
    sender_name: str | None
    seat: str | None
    reply_why: str | None = None


@dataclass(frozen=True)
class Side:
    """One side of the check: a seat, whether a clone holds it, and the session
    its holder last recorded. ``seat`` is None where the topology names no such
    seat, as for a worker whose seat names no directing seat."""

    seat: str | None
    held: bool
    record: Session | None


@dataclass(frozen=True)
class Verdict:
    """DIRECTIVE, INFORMATION or CANNOT_CHECK, and why."""

    outcome: str
    why: str


def report_sender(sides: list[Side], sender_name: str | None) -> Side | Verdict:
    """The worker's seat a report comes from, among ``sides``, the seats the
    directing seat directs: the one whose record holds the report's sender name
    (DEC-084 point 4). A Verdict where none can be: INFORMATION where no such
    seat records the name, CANNOT_CHECK where more than one does. A directing
    seat that directs no seat gets the side that names no seat."""
    if not sides:
        return Side(None, False, None)
    named = [side for side in sides if side.record is not None and side.record.name == sender_name]
    if len(named) > 1:
        seats = ", ".join(side.seat or "?" for side in named)
        return Verdict(CANNOT_CHECK, f"the seats {seats} record the same session name")
    if not named:
        return Verdict(
            INFORMATION, "the message's sender name is not one a seat this seat directs records"
        )
    return named[0]


def check(
    message: Message,
    *,
    own: Side,
    own_address: str | None,
    machine: str,
    sender: Side,
    sender_process: Reading | None,
    messaging: bool = True,
) -> Verdict:
    """Whether ``message`` is a directive to the session that takes it.

    ``own`` is the taking session's seat, with the session that seat records,
    and ``own_address`` the session's own messaging address, None where it
    cannot read one; ``machine`` the machine it runs on. ``sender`` is the seat
    the message must come from, the worker's directing seat, or for a report
    the worker's seat, with ``sender_process`` the reading of its recorded
    process. ``messaging`` is False where the harness has no messaging.

    A directive only where all of these hold: the message names ``own``'s seat;
    the sender's record names this machine and its process runs here; the
    reply address and the sender name are the recorded ones; and the taking
    session is its own seat's recorded session (DEC-084 point 2). The same
    check with the roles swapped judges a report (point 4). CANNOT_CHECK in the
    cases point 2 lists, and INFORMATION where the message itself fails a
    condition. The listing of sessions takes no part.
    """
    if not messaging:
        return Verdict(CANNOT_CHECK, "the harness has no messaging between sessions")
    if own_address is None:
        return Verdict(CANNOT_CHECK, "this session cannot read its own messaging address")
    mine = own.record
    if (
        not own.held
        or mine is None
        or mine.address != own_address
        or mine.machine != machine
        or own.seat is None
    ):
        return Verdict(
            CANNOT_CHECK, f"this session is not the one its seat {own.seat or '?'} records"
        )
    if sender.seat is None:
        return Verdict(CANNOT_CHECK, f"the seat {own.seat} names no seat to take messages from")
    theirs = sender.record
    if not sender.held:
        return Verdict(CANNOT_CHECK, f"the seat {sender.seat} is free")
    if theirs is None:
        return Verdict(CANNOT_CHECK, f"the seat {sender.seat} records no session")
    if theirs.address is None:
        return Verdict(CANNOT_CHECK, f"the seat {sender.seat}'s record holds no messaging address")
    if theirs.machine != machine:
        return Verdict(
            CANNOT_CHECK,
            f"the seat {sender.seat}'s record names another machine, {theirs.machine}",
        )
    if theirs.process is None:
        return Verdict(CANNOT_CHECK, f"the seat {sender.seat}'s record holds no process")
    if sender_process is not None and sender_process.state == ENDED:
        return Verdict(
            CANNOT_CHECK,
            f"the seat {sender.seat}'s recorded process does not run: {sender_process.why}",
        )
    if sender_process is None or sender_process.state != RUNNING:
        why = sender_process.why if sender_process is not None else "it was not read"
        return Verdict(
            CANNOT_CHECK,
            f"no one can tell whether the seat {sender.seat}'s recorded process runs: {why}",
        )
    if not message.reply_address:
        if message.reply_why:
            return Verdict(
                INFORMATION,
                f"the message's reply address is no session's address: {message.reply_why}",
            )
        return Verdict(CANNOT_CHECK, "the message carries no reply address")
    if message.seat != own.seat:
        named = f"the seat {message.seat}" if message.seat else "no seat"
        return Verdict(INFORMATION, f"the message names {named}, not {own.seat}")
    if message.reply_address != theirs.address:
        return Verdict(
            INFORMATION,
            f"the message's reply address is not the one the seat {sender.seat} records",
        )
    if message.sender_name != theirs.name:
        return Verdict(
            INFORMATION,
            f"the message's sender name is not {theirs.name}, the one the seat "
            f"{sender.seat} records",
        )
    return Verdict(
        DIRECTIVE,
        f"it comes from the session the seat {sender.seat} records, to this seat's own",
    )
