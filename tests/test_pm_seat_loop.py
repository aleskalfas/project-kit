"""The session that runs a seat's loop: `take-seat --loop` records it, and
`check-message` checks a message against the records (DEC-081 point 4, DEC-084
points 1 to 4; #3461).

A take for the loop records the session's name, machine, messaging address and
process, the last two as the backbone gives them, under DEC-084 point 3's one
rule. `check-message` reads the seat this clone holds, the seat a message must
come from and both records, and feeds the one pure check. GitHub is the
in-memory fake of the state-issue tests, the backbone's reading of the default
branch and git are the seats tests' fakes, and the backbone's readings of
sessions and processes are `Processes`, a fake of its documents.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.test_pm_seats import (
    SEATS,
    TAKE,
    VERSIONS,
    _backbone,
    _claim,
    _git,
    _key,
    _repo,
    _script,
    audit_log,
    default_branch,
    instance_identity,
    si,
    tp,
)

CHECK = _script("check-message.py")

#: Process names as the backbone gives them, which the capability passes whole.
P_OWN = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:50:500.0"
P_OLD = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:41:100.0"
P_LEAD = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:30:300.0"
OWN_ADDRESS = "/tmp/cc-socks/50.sock"
LEAD_ADDRESS = "/tmp/cc-socks/30.sock"
MACHINE = "laptop"

#: The seats, with worker-1 directed by the planner's seat.
DIRECTED = [dict(seat) for seat in SEATS]
DIRECTED[1]["directed_by"] = "planner"


class Processes:
    """The backbone's `harness session`, `recorded-process read` and `compare`,
    answered from what a test sets: this session's process and address, the
    state of each recorded name, and the pairs that name one process."""

    def __init__(
        self,
        *,
        process: str | None = P_OWN,
        address: str | None = OWN_ADDRESS,
        found: bool = True,
        states: dict[str, str] | None = None,
        same: set[tuple[str, str]] | None = None,
    ) -> None:
        self.process, self.address, self.found = process, address, found
        self.states = states or {}
        self.same = same or set()
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        request = json.loads(options["input"]) if options.get("input") else {}
        words = tuple(argv[1:3])
        if words == ("harness", "session"):
            given = [a.removeprefix("--reply=") for a in argv if a.startswith("--reply=")]
            document: dict[str, Any] = {
                "schema_version": 1,
                "adapter": "h",
                "found": self.found,
                "why": None if self.found else "no session",
                "messaging": True,
                "process": self.process,
                "process_why": None if self.process else "not found",
                "address": self.address,
                "address_why": None if self.address else "not given",
                "replies": [_reply(r) for r in given],
            }
        elif words == ("recorded-process", "read"):
            document = {
                "schema_version": 1,
                "answers": [
                    {"name": n, "state": self.states.get(n, "cannot-tell"), "by": None, "why": "w"}
                    for n in request["names"]
                ],
            }
        else:
            assert words == ("recorded-process", "compare")
            document = {
                "schema_version": 1,
                "pairs": [
                    {"names": p, "answer": "one" if tuple(p) in self.same else "two", "why": "w"}
                    for p in request["pairs"]
                ],
            }
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")

    def asked(self, *words: str) -> int:
        return sum(1 for call in self.calls if tuple(call[1 : 1 + len(words)]) == words)


def _reply(given: str) -> dict[str, Any]:
    if given.startswith("uds:"):
        return {"given": given, "address": given.removeprefix("uds:"), "why": None}
    return {"given": given, "address": None, "why": "it does not carry the form declared"}


@pytest.fixture(autouse=True)
def fresh_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(default_branch, "_read", {})
    monkeypatch.setattr(default_branch, "_warned", set())
    monkeypatch.setattr(tp, "machine", lambda: MACHINE)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / ".pkit" / "capabilities" / "project-management"
    (path / "project").mkdir(parents=True)
    return path


def _record(repo: Any, number: int, seat: str, holder: tuple[str, str], **fields: Any) -> None:
    """The session ``fields`` give, recorded on ``seat`` by its holder."""
    session = audit_log.event(si.SESSION, key=seat, clone=holder[1], **fields)
    repo.post(number, audit_log.build(session, versions=VERSIONS), author=holder[0])


def _recorded(repo: Any, number: int, seat: str) -> si.Session | None:
    found = si.read(
        number, "seat", seat, si.StateRun(repo, si.Writers.closed(["me", "you"]), VERSIONS)
    )
    assert found.fold is not None
    return found.fold.session


def _take(root: Path, repo: Any, processes: Processes, **kw: Any) -> int:
    loop = TAKE.Loop(kw.pop("session_name", "worker-1"), yes=kw.pop("yes", False))
    return TAKE.take_seat(
        root,
        name=kw.pop("name", "worker-1"),
        role=None,
        agent="project-manager",
        login="me",
        gh=repo,
        run=_backbone(),
        git=_git(),
        versions=VERSIONS,
        loop=loop,
        processes_run=processes,
        **kw,
    )


# ---- take-seat --loop ---------------------------------------------------------------


def test_a_take_for_the_loop_records_its_session_on_a_free_seat(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo()
    assert _take(root, repo, Processes()) == 0
    assert _recorded(repo, 12, "worker-1") == si.Session("worker-1", MACHINE, OWN_ADDRESS, P_OWN)
    assert "recorded on #12" in capsys.readouterr().out


def test_a_session_already_recorded_posts_nothing_again(root: Path) -> None:
    repo = _repo(worker_1=("me", _key(root)))
    instance_identity.write_seat_hint(root, "worker-1")
    _record(
        repo, 12, "worker-1", ("me", _key(root)),
        name="worker-1", machine=MACHINE, address=OWN_ADDRESS, process=P_OWN,
    )  # fmt: skip
    posted = len(repo.bodies(12))
    processes = Processes()
    assert _take(root, repo, processes) == 0
    assert len(repo.bodies(12)) == posted
    assert processes.asked("recorded-process") == 0


def test_a_take_for_the_loop_replaces_an_ended_process_or_its_own_without_asking(
    root: Path,
) -> None:
    for processes in (Processes(states={P_OLD: "ended"}), Processes(same={(P_OLD, P_OWN)})):
        repo = _repo(worker_1=("me", _key(root)))
        instance_identity.write_seat_hint(root, "worker-1")
        _record(
            repo, 12, "worker-1", ("me", _key(root)),
            name="worker-1", machine=MACHINE, address="/tmp/cc-socks/41.sock", process=P_OLD,
        )  # fmt: skip
        assert _take(root, repo, processes) == 0
        recorded = _recorded(repo, 12, "worker-1")
        assert recorded is not None and recorded.process == P_OWN


def test_another_live_session_is_replaced_only_on_the_persons_word(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(worker_1=("me", _key(root)))
    instance_identity.write_seat_hint(root, "worker-1")
    _record(
        repo, 12, "worker-1", ("me", _key(root)),
        name="worker-1", machine=MACHINE, address="/tmp/cc-socks/41.sock", process=P_OLD,
    )  # fmt: skip
    live = Processes(states={P_OLD: "running"})
    posted = len(repo.bodies(12))
    assert _take(root, repo, live) == 0
    captured = capsys.readouterr()
    assert len(repo.bodies(12)) == posted
    assert "another live session" in captured.out and "[unrecorded]" in captured.out
    assert "--yes" in captured.err
    assert _take(root, repo, live, yes=True) == 0
    recorded = _recorded(repo, 12, "worker-1")
    assert recorded is not None and recorded.process == P_OWN


def test_a_session_whose_address_is_not_given_records_its_name_and_machine_only(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo()
    assert _take(root, repo, Processes(process=None, address=None)) == 0
    assert _recorded(repo, 12, "worker-1") == si.Session("worker-1", MACHINE)
    assert "no message to or from it counts as a directive" in capsys.readouterr().err


def test_a_dry_run_for_the_loop_records_nothing(root: Path) -> None:
    repo = _repo()
    processes = Processes()
    assert _take(root, repo, processes, dry_run=True) == 0
    assert repo.writes() == [] and processes.calls == []


def test_the_session_name_is_given_or_read_from_the_environment() -> None:
    assert TAKE.session_name("lead", {}) == ("lead", None)
    assert TAKE.session_name(None, {"PKIT_SESSION_NAME": " worker-2 "}) == ("worker-2", None)
    for bad in (None, "a\nb", "x" * 101):
        name, why = TAKE.session_name(bad, {})
        assert name is None and why


# ---- check-message ------------------------------------------------------------------


def _seated(root: Path, *, lead_process: str = P_LEAD) -> Any:
    """worker-1 held by this clone, directed by the planner's seat, held by
    another clone; each seat's session recorded."""
    me, you = ("me", _key(root)), ("you", "k7")
    repo = _repo()
    _claim(repo, 11, "planner", you)
    _claim(repo, 12, "worker-1", me)
    instance_identity.write_seat_hint(root, "worker-1")
    _record(
        repo, 11, "planner", you,
        name="planner", machine=MACHINE, address=LEAD_ADDRESS, process=lead_process,
    )  # fmt: skip
    _record(
        repo, 12, "worker-1", me,
        name="worker-1", machine=MACHINE, address=OWN_ADDRESS, process=P_OWN,
    )  # fmt: skip
    return repo


def _check(root: Path, repo: Any, processes: Processes, **message: str | None) -> Any:
    return CHECK.judge(
        root,
        message,
        login="me",
        gh=repo,
        run=_backbone(),
        git=_git(DIRECTED),
        versions=VERSIONS,
        processes_run=processes,
    )


FROM_LEAD = {"reply_address": f"uds:{LEAD_ADDRESS}", "sender_name": "planner", "seat": "worker-1"}


def test_a_message_from_the_directing_seats_recorded_session_is_a_directive(root: Path) -> None:
    repo = _seated(root)
    verdict = _check(root, repo, Processes(states={P_LEAD: "running"}), **FROM_LEAD)
    assert verdict.outcome == "directive"


def test_a_message_that_fails_a_condition_is_information(root: Path) -> None:
    repo = _seated(root)
    live = Processes(states={P_LEAD: "running"})
    stray = {**FROM_LEAD, "reply_address": "uds:/tmp/cc-socks/99.sock"}
    assert _check(root, repo, live, **stray).outcome == "information"
    elsewhere = {**FROM_LEAD, "seat": "worker-2"}
    assert _check(root, repo, live, **elsewhere).outcome == "information"
    unformed = {**FROM_LEAD, "reply_address": LEAD_ADDRESS}
    verdict = _check(root, repo, live, **unformed)
    assert verdict.outcome == "information" and "no session's address" in verdict.why


def test_a_message_cannot_be_checked_where_the_sender_cannot_be_told_of(root: Path) -> None:
    repo = _seated(root)
    verdict = _check(root, repo, Processes(), **FROM_LEAD)
    assert verdict.outcome == "cannot-check" and "no one can tell" in verdict.why
    ended = _check(root, repo, Processes(states={P_LEAD: "ended"}), **FROM_LEAD)
    assert ended.outcome == "cannot-check"


def test_a_session_that_is_not_its_seats_recorded_one_cannot_check(root: Path) -> None:
    repo = _seated(root)
    other = Processes(address="/tmp/cc-socks/88.sock", states={P_LEAD: "running"})
    verdict = _check(root, repo, other, **FROM_LEAD)
    assert verdict.outcome == "cannot-check" and "not the one its seat" in verdict.why


def test_a_clone_that_holds_no_seat_cannot_check(root: Path) -> None:
    repo = _repo()
    verdict = _check(root, repo, Processes(), **FROM_LEAD)
    assert verdict.outcome == "cannot-check" and "holds no seat" in verdict.why


def test_a_report_from_a_directed_workers_recorded_session_counts(root: Path) -> None:
    """The directing seat's side: the worker whose record holds the sender name."""
    me, you = ("me", _key(root)), ("you", "k7")
    repo = _repo()
    _claim(repo, 11, "planner", me)
    _claim(repo, 12, "worker-1", you)
    instance_identity.write_seat_hint(root, "planner")
    _record(
        repo, 11, "planner", me,
        name="planner", machine=MACHINE, address=LEAD_ADDRESS, process=P_LEAD,
    )  # fmt: skip
    _record(
        repo, 12, "worker-1", you,
        name="worker-1", machine=MACHINE, address=OWN_ADDRESS, process=P_OWN,
    )  # fmt: skip
    lead = Processes(process=P_LEAD, address=LEAD_ADDRESS, states={P_OWN: "running"})
    report = {"reply_address": f"uds:{OWN_ADDRESS}", "sender_name": "worker-1", "seat": "planner"}
    assert _check(root, repo, lead, **report).outcome == "directive"
    unknown = {**report, "sender_name": "worker-9"}
    assert _check(root, repo, lead, **unknown).outcome == "information"


@pytest.mark.parametrize(
    "text", ["not json", "[]", '{"seat": 3}', '{"reply_address": ["uds:/tmp/x"]}']
)
def test_a_request_that_is_no_object_of_strings_is_refused(text: str) -> None:
    message, why = CHECK.read_message(text)
    assert message is None and why


def test_a_request_reads_each_key_or_none() -> None:
    message, _ = CHECK.read_message('{"seat": "worker-1", "extra": 1}')
    assert message == {"reply_address": None, "sender_name": None, "seat": "worker-1"}
