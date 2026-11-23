"""The sessions that run seats' loops: whether one runs, when a loop records
itself, and whether a message is a directive (DEC-081, DEC-084).

[project-management:DEC-081-delegation-between-seats] lets a worker's directing
seat message it, to wake it or to name a ready Task it may take next.
[project-management:DEC-084-seat-session-address] decides how a worker tells a
directive from information: each seat's state issue records the session that
runs its loop, by its name, machine, messaging address and process
(``_lib/state_issues``), and a message counts only where it comes from the
directing seat's recorded session to the worker's own.

This module holds the three judgements DEC-084 makes, as pure functions, so
both sides of a seat's messages use one copy of each and the commands only
feed them:

* :func:`read_process` reads whether a recorded process runs, from what a
  command observed of it here, the strongest way the observations and the
  record allow (DEC-084 point 2);
* :func:`recording` says whether a loop records itself without asking, only on
  the person's word, or not at all, since its record already holds it (DEC-084
  point 3);
* :func:`check` says whether a message is a directive, information, or cannot
  be checked, with why (DEC-084 points 2 and 4).

It reads nothing and runs nothing: no ``gh`` call, no process, no file and no
harness. A caller observes the process, reads the state issues, takes its own
session's facts from the backbone, and brings each address into the one form
the adapter's declaration gives, before it calls these.

Like the guard on a claim (DEC-035 point 6), the check catches the mistakes of
sessions that follow the procedure, and stops no one who means to pass as
another (DEC-084 point 5).
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from _lib.state_issues import Session
except ImportError:  # pragma: no cover - a test that puts `_lib` itself on the path
    from state_issues import Session  # type: ignore[no-redef]

# ---- whether a recorded process runs (DEC-084 point 2 and its Terms) ------------

#: What a reading says of a recorded process.
RUNS = "runs"
ENDED = "ended"
CANNOT_TELL = "cannot-tell"

#: The two readings, the strongest first.
BY_START = "its id and start time"
BY_ID = "its id alone"

#: What a command saw of a process's start time: the time itself is a string;
#: these say it saw no process under the id, or could not read the start time.
NO_PROCESS = "no-process"
UNREADABLE = "unreadable"

#: What a null signal, sent only to test whether a process with an id exists,
#: returned: delivered, refused for lack of permission, no such process, or
#: another failure.
DELIVERED = "delivered"
REFUSED = "refused"
NO_SUCH = "no-such"
FAILED = "failed"


@dataclass(frozen=True)
class ProcessReading:
    """Whether a recorded process runs: RUNS, ENDED or CANNOT_TELL, the reading
    that told (BY_START or BY_ID, None where none told), and why."""

    state: str
    by: str | None
    why: str

    @property
    def runs(self) -> bool:
        return self.state == RUNS


def read_process(
    recorded: Session,
    *,
    seen_start: str | None,
    signal: str | None,
    id_alone: bool,
) -> ProcessReading:
    """Whether the process ``recorded`` names runs on this machine, as a command
    here observed it.

    ``seen_start`` is the start time the command read for the recorded id, or
    NO_PROCESS where it read that no process holds the id, or UNREADABLE where
    it could not read it, or None where it did not try. ``signal`` is what a
    null signal to the id returned, or None where none was sent. ``id_alone``
    says whether the adapter's declaration permits reading a process by its id
    alone from where the command runs, as it does only where a null signal was
    measured there to tell a running id from a free one.

    By its id and start time wherever both the record and the command hold one:
    the same time runs, another has ended, since another process took its id. A
    command that saw no process under the id reads it as ended. Otherwise, by
    the id alone only where ``id_alone`` permits: a signal delivered or refused
    runs, since only a process that holds the id refuses it, and no such
    process has ended. Otherwise no one can tell, and a start time that could
    not be read is never taken for a process that does not run.
    """
    if recorded.pid is None:
        return ProcessReading(CANNOT_TELL, None, "the record holds no process")
    pid = recorded.pid
    if seen_start == NO_PROCESS:
        return ProcessReading(ENDED, BY_START, f"no process holds the id {pid}")
    seen = seen_start if seen_start not in (None, UNREADABLE) else None
    if seen is not None and recorded.started:
        if seen == recorded.started:
            return ProcessReading(RUNS, BY_START, f"process {pid} started when it was recorded")
        return ProcessReading(
            ENDED, BY_START, f"the process that holds the id {pid} started at another time"
        )
    if not id_alone:
        if not recorded.started:
            return ProcessReading(
                CANNOT_TELL,
                None,
                "the record holds no start time, and the adapter's declaration permits no "
                "reading by the process's id alone from here",
            )
        return ProcessReading(
            CANNOT_TELL,
            None,
            f"the start time of process {pid} cannot be read here, and the adapter's "
            "declaration permits no reading by its id alone from here",
        )
    if seen is not None or signal in (DELIVERED, REFUSED):
        return ProcessReading(RUNS, BY_ID, f"a process holds the id {pid}")
    if signal == NO_SUCH:
        return ProcessReading(ENDED, BY_ID, f"no process holds the id {pid}")
    return ProcessReading(
        CANNOT_TELL, None, f"neither the start time nor a signal told of process {pid}"
    )


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


def recording(record: Session | None, own: Session, recorded: ProcessReading | None) -> Recording:
    """Whether a loop records ``own``, its session, over ``record``, its seat's
    record, with ``recorded`` the reading of the recorded process, where one
    was taken.

    ALREADY where the record holds ``own`` whole, so nothing is posted. RECORD
    without asking where the record holds no session, the recorded process is
    the loop's own, or it has ended. The recorded process is the loop's own, or
    an ended one whose id the loop's process now holds, where both name one
    machine and one process id. ASK otherwise: the record is another live
    session's, or one no one can tell of, and only the person's word, given in
    the loop's own session, replaces it.
    """
    if record is None:
        return Recording(RECORD, "the seat records no session")
    if record == own:
        return Recording(ALREADY, "the seat already records this session")
    if record.machine == own.machine and record.pid is not None and record.pid == own.pid:
        return Recording(RECORD, "the recorded process is this session's own")
    if record.machine != own.machine:
        return Recording(
            ASK,
            f"the seat records the session {record.name} on another machine, "
            f"{record.machine}, whose process no one here can tell of",
        )
    if recorded is not None and recorded.state == ENDED:
        return Recording(RECORD, f"the recorded session's process has ended: {recorded.why}")
    if recorded is not None and recorded.state == RUNS:
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
    one it is meant for. Each is None where the message carries none."""

    reply_address: str | None
    sender_name: str | None
    seat: str | None


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


def check(
    message: Message,
    *,
    own: Side,
    own_address: str | None,
    machine: str,
    sender: Side,
    sender_process: ProcessReading | None,
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
    if sender_process is None or sender_process.state == CANNOT_TELL:
        why = sender_process.why if sender_process is not None else "it was not read"
        return Verdict(
            CANNOT_CHECK,
            f"no one can tell whether the seat {sender.seat}'s recorded process runs: {why}",
        )
    if sender_process.state == ENDED:
        return Verdict(
            CANNOT_CHECK,
            f"the seat {sender.seat}'s recorded process does not run: {sender_process.why}",
        )
    if not message.reply_address:
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
