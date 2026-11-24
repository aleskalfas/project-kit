"""The documents `pkit harness session` and `pkit recorded-process` print hold their
contracts (ADR-097 point 7; ADR-100 point 9; ADR-103).

Each command runs in the test's own process against an operating system the test sets
(`tests/fake_processes.py`), in a project of the test's own whose adapter declares a
session. The forms and values a short state does not reach are built through the
function the command prints them with. `tests/test_backbone_documents.py` gathers the
contracts here into its ratchet.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from project_kit import harness_session as hs
from project_kit import recorded_processes as rp
from tests.backbone_documents import JSON_OPTION, document_of, invoke
from tests.document_contracts import Contract, Form, check
from tests.fake_processes import FakeSystem
from tests.test_harness_session import _project  # pyright: ignore[reportPrivateUsage]

_STATES = frozenset({rp.RUNNING, rp.ENDED, rp.CANNOT_TELL})
_READINGS = frozenset({rp.BY_START_TIME, rp.BY_ID_ALONE, rp.BY_EARLIER_BOOT})
_ANSWERS = frozenset({rp.ONE, rp.TWO, rp.CANNOT_TELL})

SESSION = Contract(
    name="pkit harness session --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "adapter": "str|null",
                "found": "bool",
                "why": "str|null",
                "messaging": "bool",
                "process": "str|null",
                "process_why": "str|null",
                "address": "str|null",
                "address_why": "str|null",
                "replies": "list",
                "replies[]": "object",
                "replies[].given": "str",
                "replies[].address": "str|null",
                "replies[].why": "str|null",
            }
        )
    },
)

READ = Contract(
    name="pkit recorded-process read --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "answers": "list",
                "answers[]": "object",
                "answers[].name": "str",
                "answers[].state": "str",
                "answers[].by": "str|null",
                "answers[].why": "str",
            }
        )
    },
    sets={"answers[].state": _STATES, "answers[].by": _READINGS},
)

COMPARE = Contract(
    name="pkit recorded-process compare --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "pairs": "list",
                "pairs[]": "object",
                "pairs[].names": "list",
                "pairs[].names[]": "str",
                "pairs[].answer": "str",
                "pairs[].why": "str",
            }
        )
    },
    sets={"pairs[].answer": _ANSWERS},
)

#: A declaration of a session, as an adapter of the test's own ships it.
DECLARED = (
    "schema_version: 1\n"
    "process:\n  variable: H_PID\n"
    "messaging:\n  variable: H_SOCKET\n  reply_prefix: 'uds:'\n"
    "  names_process: '/tmp/socks/(?P<pid>[1-9][0-9]*)\\.sock'\n"
    "id_alone_platforms: [darwin]\n"
)


def _in_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, system: FakeSystem, declared: str | None
) -> Path:
    root = _project(tmp_path, {"h": declared})
    monkeypatch.chdir(root)
    monkeypatch.setattr(rp, "this_system", lambda: system)
    return root


def _session(*replies: str) -> dict[str, Any]:
    return document_of(
        invoke("harness", "session", *(f"--reply={r}" for r in replies), JSON_OPTION)
    )


def test_the_harness_session_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")}, signals={42: rp.FOUND})
    root = _in_project(tmp_path / "found", monkeypatch, system, DECLARED)
    monkeypatch.setenv("H_PID", "42")
    monkeypatch.setenv("H_SOCKET", "/tmp/socks/42.sock")
    documents = [_session("uds:/tmp/socks/7.sock", "/tmp/socks/7.sock")]
    monkeypatch.setenv("H_SOCKET", "/Users/someone/42.sock")
    documents.append(_session())
    hidden = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    documents.append(hs.read(root, {"H_PID": "42"}, hidden).document())
    monkeypatch.delenv("H_PID")
    documents.append(_session())
    _in_project(tmp_path / "none", monkeypatch, system, None)
    documents.append(_session("uds:/tmp/socks/7.sock"))
    check(SESSION, {"answer": documents})


def _named(system: FakeSystem, pid: int) -> str:
    reader = rp.Reader(rp.space_of(system.space(), "https://github.com/o/r"), system.platform)
    named = rp.name(pid, reader, system)
    assert named.name is not None, named.why
    return named.name


def test_the_recorded_process_read_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    system = FakeSystem(
        entries={42: rp.Entry(True, "100.0"), 43: rp.Entry(True, "200.0")},
        signals={42: rp.FOUND, 9: rp.FOUND},
    )
    _in_project(tmp_path, monkeypatch, system, DECLARED)
    running, ended = _named(system, 42), _named(system, 43)
    del system.entries[43]
    request = json.dumps({"names": [running, ended, "no name"]})
    printed = document_of(invoke("recorded-process", "read", JSON_OPTION, stdin=request))
    system.entries[44] = rp.Entry(None, why="denied")
    system.signals[44] = rp.FOUND
    bare = _named(system, 44)
    space = rp.space_of(system.space(), "https://github.com/o/r")
    by_id = rp.read_document({"names": [bare]}, rp.Reader(space, "darwin", True, 9), system)
    system.raw = rp.RawSpace("machine-1", "boot-2", None, False, True)
    later = rp.read_document(
        {"names": [running]},
        rp.Reader(rp.space_of(system.space(), "https://github.com/o/r"), "darwin"),
        system,
    )
    check(
        READ,
        {"answer": [printed, by_id, later]},
        enumerations={"answers[].state": _STATES, "answers[].by": _READINGS},
    )


def test_the_recorded_process_compare_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    system = FakeSystem(entries={42: rp.Entry(True, "100.0"), 43: rp.Entry(True, "200.0")})
    _in_project(tmp_path, monkeypatch, system, DECLARED)
    one, other = _named(system, 42), _named(system, 43)
    request = json.dumps({"pairs": [[one, one], [one, other], [one, "no name"]]})
    document = document_of(invoke("recorded-process", "compare", JSON_OPTION, stdin=request))
    check(COMPARE, {"answer": [document]}, enumerations={"pairs[].answer": _ANSWERS})


@pytest.mark.parametrize(
    ("command", "request_"),
    [
        ("read", '{"names": "x"}'),
        ("read", '{"names": [1]}'),
        ("compare", '{"pairs": [["a"]]}'),
        ("compare", "not json"),
    ],
)
def test_a_refused_request_prints_no_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str, request_: str
) -> None:
    _in_project(tmp_path, monkeypatch, FakeSystem(), DECLARED)
    result = invoke("recorded-process", command, JSON_OPTION, stdin=request_)
    assert result.exit_code == 1
    assert result.stdout == ""


CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "harness session": (SESSION,),
    "recorded-process read": (READ,),
    "recorded-process compare": (COMPARE,),
}
