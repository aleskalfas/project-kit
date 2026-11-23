"""The sessions that run seats' loops (DEC-081, DEC-084; #3461).

`_lib/seat_sessions` holds DEC-084's three judgements as pure functions:

- whether a recorded process runs, read by its id and start time wherever both
  are held, by its id alone only where the adapter's declaration permits it,
  and otherwise not at all, a start time that cannot be read never taken for a
  process that does not run (point 2);
- whether a loop records itself without asking, only on the person's word, or
  not at all (point 3);
- whether a message is a directive, information, or cannot be checked, for a
  directive and, with the roles swapped, for a report (points 2 and 4).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import seat_sessions as ss  # noqa: E402
from _lib.state_issues import Session  # noqa: E402

START = "Mon Nov 23 15:00:00 2026"
LATER = "Mon Nov 23 16:00:00 2026"
LEAD = Session("planner", "laptop", "/tmp/cc-socks/41.sock", 41, START)
WORKER = Session("worker-1", "laptop", "/tmp/cc-socks/77.sock", 77, START)


# ---- whether a recorded process runs ---------------------------------------------


def test_a_process_read_by_its_id_and_start_time_runs_only_at_the_recorded_time() -> None:
    reading = ss.read_process(LEAD, seen_start=START, signal=None, id_alone=False)
    assert (reading.state, reading.by) == (ss.RUNS, ss.BY_START)
    other = ss.read_process(LEAD, seen_start=LATER, signal=ss.REFUSED, id_alone=True)
    assert (other.state, other.by) == (ss.ENDED, ss.BY_START)
    assert "another time" in other.why


def test_a_process_no_one_holds_the_id_of_has_ended() -> None:
    for id_alone in (False, True):
        reading = ss.read_process(LEAD, seen_start=ss.NO_PROCESS, signal=None, id_alone=id_alone)
        assert reading.state == ss.ENDED


@pytest.mark.parametrize("signal", [ss.DELIVERED, ss.REFUSED])
def test_by_its_id_alone_a_signal_delivered_or_refused_runs(signal: str) -> None:
    """Outside the sandbox a signal is delivered, inside it refused, and either
    tells that a process holds the id."""
    reading = ss.read_process(LEAD, seen_start=ss.UNREADABLE, signal=signal, id_alone=True)
    assert (reading.state, reading.by) == (ss.RUNS, ss.BY_ID)


def test_by_its_id_alone_no_such_process_has_ended() -> None:
    reading = ss.read_process(LEAD, seen_start=ss.UNREADABLE, signal=ss.NO_SUCH, id_alone=True)
    assert (reading.state, reading.by) == (ss.ENDED, ss.BY_ID)


def test_a_start_time_that_cannot_be_read_is_not_a_process_that_does_not_run() -> None:
    """Without the declaration's leave to read by the id alone, a start time the
    command cannot read tells nothing, whatever the signal says."""
    for signal in (None, ss.NO_SUCH, ss.REFUSED):
        reading = ss.read_process(LEAD, seen_start=ss.UNREADABLE, signal=signal, id_alone=False)
        assert reading.state == ss.CANNOT_TELL and reading.by is None
        assert "cannot be read here" in reading.why
    failed = ss.read_process(LEAD, seen_start=ss.UNREADABLE, signal=ss.FAILED, id_alone=True)
    assert failed.state == ss.CANNOT_TELL


def test_a_record_with_no_start_time_is_read_by_its_id_alone_or_not_at_all() -> None:
    bare = Session("planner", "laptop", "/tmp/cc-socks/41.sock", 41)
    assert ss.read_process(bare, seen_start=START, signal=None, id_alone=False).state == (
        ss.CANNOT_TELL
    )
    reading = ss.read_process(bare, seen_start=START, signal=None, id_alone=True)
    assert (reading.state, reading.by) == (ss.RUNS, ss.BY_ID)
    assert ss.read_process(bare, seen_start=None, signal=ss.NO_SUCH, id_alone=True).state == (
        ss.ENDED
    )


def test_a_record_with_no_process_cannot_be_told_of() -> None:
    none = Session("planner", "laptop", "/tmp/cc-socks/41.sock")
    reading = ss.read_process(none, seen_start=START, signal=ss.REFUSED, id_alone=True)
    assert reading.state == ss.CANNOT_TELL and reading.why == "the record holds no process"


# ---- when a loop records itself ----------------------------------------------------

RUNNING = ss.ProcessReading(ss.RUNS, ss.BY_START, "it runs")
ENDED = ss.ProcessReading(ss.ENDED, ss.BY_START, "no process holds the id 41")
UNKNOWN = ss.ProcessReading(ss.CANNOT_TELL, None, "its start time cannot be read here")
NEW = Session("planner", "laptop", "/tmp/cc-socks/50.sock", 50, LATER)


def test_a_loop_records_itself_without_asking_where_the_seat_records_no_session() -> None:
    assert ss.recording(None, NEW, None).action == ss.RECORD


def test_a_loop_already_recorded_posts_nothing() -> None:
    assert ss.recording(LEAD, LEAD, RUNNING).action == ss.ALREADY


def test_a_loop_records_itself_over_an_ended_process_without_asking() -> None:
    out = ss.recording(LEAD, NEW, ENDED)
    assert out.action == ss.RECORD and "ended" in out.why


def test_a_loop_records_itself_over_its_own_process_without_asking() -> None:
    """Its own process, or an ended one whose id its process now holds."""
    moved = Session("planner", "laptop", "/tmp/cc-socks/41.sock", 41, LATER)
    assert ss.recording(LEAD, moved, RUNNING).action == ss.RECORD


def test_a_loop_asks_the_person_over_another_live_process_or_one_no_one_can_tell_of() -> None:
    assert ss.recording(LEAD, NEW, RUNNING).action == ss.ASK
    assert ss.recording(LEAD, NEW, UNKNOWN).action == ss.ASK
    assert ss.recording(LEAD, NEW, None).action == ss.ASK
    elsewhere = Session("planner", "desktop", "/tmp/cc-socks/41.sock", 41, START)
    out = ss.recording(elsewhere, NEW, None)
    assert out.action == ss.ASK and "another machine" in out.why


# ---- whether a message is a directive ----------------------------------------------

WORKER_SIDE = ss.Side("worker-1", True, WORKER)
LEAD_SIDE = ss.Side("planner", True, LEAD)
FROM_LEAD = ss.Message("/tmp/cc-socks/41.sock", "planner", "worker-1")


def _directive(
    message: ss.Message = FROM_LEAD,
    *,
    own: ss.Side = WORKER_SIDE,
    own_address: str | None = "/tmp/cc-socks/77.sock",
    machine: str = "laptop",
    sender: ss.Side = LEAD_SIDE,
    process: ss.ProcessReading | None = RUNNING,
    messaging: bool = True,
) -> ss.Verdict:
    return ss.check(
        message,
        own=own,
        own_address=own_address,
        machine=machine,
        sender=sender,
        sender_process=process,
        messaging=messaging,
    )


def test_a_message_from_the_recorded_session_to_the_seats_own_is_a_directive() -> None:
    assert _directive().outcome == ss.DIRECTIVE


def test_a_message_that_names_another_seat_or_none_is_information() -> None:
    for seat in ("worker-2", None):
        verdict = _directive(ss.Message("/tmp/cc-socks/41.sock", "planner", seat))
        assert verdict.outcome == ss.INFORMATION and "names" in verdict.why


def test_another_reply_address_is_information() -> None:
    verdict = _directive(ss.Message("/tmp/cc-socks/99.sock", "planner", "worker-1"))
    assert verdict.outcome == ss.INFORMATION and "reply address" in verdict.why


def test_another_sender_name_is_information() -> None:
    verdict = _directive(ss.Message("/tmp/cc-socks/41.sock", "someone", "worker-1"))
    assert verdict.outcome == ss.INFORMATION and "sender name" in verdict.why


def test_a_record_naming_another_machine_cannot_be_checked() -> None:
    elsewhere = ss.Side("planner", True, Session("planner", "desktop", LEAD.address, 41, START))
    verdict = _directive(sender=elsewhere)
    assert verdict.outcome == ss.CANNOT_CHECK and "another machine" in verdict.why


def test_a_recorded_process_that_ended_or_no_one_can_tell_of_cannot_be_checked() -> None:
    assert _directive(process=ENDED).outcome == ss.CANNOT_CHECK
    unknown = _directive(process=UNKNOWN)
    assert unknown.outcome == ss.CANNOT_CHECK and "no one can tell" in unknown.why
    assert _directive(process=None).outcome == ss.CANNOT_CHECK


def test_a_session_that_is_not_its_seats_recorded_one_cannot_check() -> None:
    """Such as one the person opens in the worker's clone, which shares its name."""
    verdict = _directive(own_address="/tmp/cc-socks/88.sock")
    assert verdict.outcome == ss.CANNOT_CHECK and "not the one its seat" in verdict.why
    unrecorded = _directive(own=ss.Side("worker-1", True, None))
    assert unrecorded.outcome == ss.CANNOT_CHECK
    elsewhere = _directive(machine="desktop")
    assert elsewhere.outcome == ss.CANNOT_CHECK


def test_a_session_with_no_messaging_address_to_read_cannot_check() -> None:
    verdict = _directive(own_address=None)
    assert verdict.outcome == ss.CANNOT_CHECK and "messaging address" in verdict.why


@pytest.mark.parametrize(
    ("sender", "why"),
    [
        (ss.Side(None, False, None), "names no seat"),
        (ss.Side("planner", False, None), "is free"),
        (ss.Side("planner", True, None), "records no session"),
        (ss.Side("planner", True, Session("planner", "laptop")), "no messaging address"),
    ],
)
def test_the_directing_seat_named_held_and_recorded_or_the_check_cannot_pass(
    sender: ss.Side, why: str
) -> None:
    verdict = _directive(sender=sender)
    assert verdict.outcome == ss.CANNOT_CHECK and why in verdict.why


def test_a_message_with_no_reply_address_or_no_messaging_cannot_be_checked() -> None:
    assert _directive(ss.Message(None, "planner", "worker-1")).outcome == ss.CANNOT_CHECK
    assert _directive(messaging=False).outcome == ss.CANNOT_CHECK


def test_a_report_is_checked_the_same_way_with_the_roles_swapped() -> None:
    report = ss.Message("/tmp/cc-socks/77.sock", "worker-1", "planner")
    verdict = _directive(
        report, own=LEAD_SIDE, own_address="/tmp/cc-socks/41.sock", sender=WORKER_SIDE
    )
    assert verdict.outcome == ss.DIRECTIVE
    stray = ss.Message("/tmp/cc-socks/78.sock", "worker-1", "planner")
    assert (
        _directive(
            stray, own=LEAD_SIDE, own_address="/tmp/cc-socks/41.sock", sender=WORKER_SIDE
        ).outcome
        == ss.INFORMATION
    )
