"""The sessions that run seats' loops (DEC-081, DEC-084; #3461).

`_lib/seat_sessions` holds DEC-084's two judgements as pure functions, fed the
backbone's answers on whether a recorded process runs and whether two process
names name one process (ADR-103):

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

from _lib import processes as pr  # noqa: E402
from _lib import seat_sessions as ss  # noqa: E402
from _lib.state_issues import Session  # noqa: E402

#: Process names as the backbone gives them, which the capability passes whole.
P41 = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:41:1795515261.273034"
P77 = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:77:1795515300.000001"
P50 = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:50:1795518861.000001"
LEAD = Session("planner", "laptop", "/tmp/cc-socks/41.sock", P41)
WORKER = Session("worker-1", "laptop", "/tmp/cc-socks/77.sock", P77)

RUNNING = pr.Reading(pr.RUNNING, "a process holds the id 41, started at the recorded time")
ENDED = pr.Reading(pr.ENDED, "no process holds the id 41")
UNKNOWN = pr.Reading(pr.CANNOT_TELL, "this command cannot read its own process space whole")


# ---- when a loop records itself ----------------------------------------------------

NEW = Session("planner", "laptop", "/tmp/cc-socks/50.sock", P50)


def _recording(
    record: Session | None, *, recorded: pr.Reading | None = None, same: str | None = pr.TWO
) -> ss.Recording:
    return ss.recording(record, NEW, recorded=recorded, same=same)


def test_a_loop_records_itself_without_asking_where_the_seat_records_no_session() -> None:
    assert _recording(None, same=None).action == ss.RECORD


def test_a_loop_already_recorded_posts_nothing() -> None:
    assert ss.recording(NEW, NEW, recorded=None, same=None).action == ss.ALREADY


def test_a_loop_records_itself_over_an_ended_process_without_asking() -> None:
    out = _recording(LEAD, recorded=ENDED)
    assert out.action == ss.RECORD and "ended" in out.why


def test_a_loop_records_itself_over_its_own_process_without_asking() -> None:
    """The backbone answers that the recorded name and the loop's own name one
    process, such as where the session's address moved."""
    moved = Session("planner", "laptop", "/tmp/cc-socks/99.sock", P50)
    out = _recording(moved, recorded=RUNNING, same=pr.ONE)
    assert out.action == ss.RECORD and "own" in out.why


def test_a_loop_asks_the_person_over_another_live_process_or_one_no_one_can_tell_of() -> None:
    live = _recording(LEAD, recorded=RUNNING)
    assert live.action == ss.ASK and "another live session" in live.why
    unknown = _recording(LEAD, recorded=UNKNOWN, same=pr.CANNOT_TELL)
    assert unknown.action == ss.ASK and "no one can tell" in unknown.why
    assert _recording(LEAD, recorded=None, same=None).action == ss.ASK


def test_a_record_with_no_process_is_one_no_one_can_tell_of() -> None:
    bare = Session("planner", "laptop")
    assert _recording(bare, recorded=None, same=None).action == ss.ASK


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
    process: pr.Reading | None = RUNNING,
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
    elsewhere = ss.Side("planner", True, Session("planner", "desktop", LEAD.address, P41))
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
        (
            ss.Side("planner", True, Session("planner", "laptop", "/tmp/cc-socks/41.sock")),
            "holds no process",
        ),
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
