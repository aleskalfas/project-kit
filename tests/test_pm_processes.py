"""The capability's reading of a session and of recorded processes, through the backbone
(`_lib/processes`; ADR-103; DEC-084; #3461).

Each call runs `pkit` with the argument list and the request the backbone's commands
read, and reads only their documents. A run that gives no document, a document it cannot
read and a value it does not know each read as *cannot tell*, and a session as none
found. `tests/test_document_callers.py` holds the readings to the documents' contracts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import processes as pr  # noqa: E402

P41 = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:41:100.0"
P42 = "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:42:200.0"


class Backbone:
    """`pkit` stood in: each call's argument list and request, answered by one run."""

    def __init__(self, document: object = None, *, code: int = 0, stderr: str = "") -> None:
        self.document = document
        self.code = code
        self.stderr = stderr
        self.calls: list[tuple[list[str], Any]] = []

    def __call__(self, argv: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        given = options.get("input")
        self.calls.append((list(argv), json.loads(given) if given is not None else None))
        out = json.dumps(self.document) if self.document is not None else ""
        return subprocess.CompletedProcess(argv, self.code, out, self.stderr)


def _session_document(**changes: object) -> dict[str, object]:
    return {
        "schema_version": 1,
        "adapter": "claude-code",
        "found": True,
        "why": None,
        "messaging": True,
        "process": P41,
        "process_why": None,
        "address": "/tmp/cc-socks/41.sock",
        "address_why": None,
        "replies": [
            {"given": "uds:/tmp/cc-socks/42.sock", "address": "/tmp/cc-socks/42.sock", "why": None}
        ],
        **changes,
    }


def test_the_session_is_asked_with_each_reply_and_read_whole() -> None:
    backbone = Backbone(_session_document())
    session = pr.session(["uds:/tmp/cc-socks/42.sock"], run=backbone)
    assert backbone.calls == [
        (["pkit", "harness", "session", "--json", "--reply=uds:/tmp/cc-socks/42.sock"], None)
    ]
    assert session.found and session.messaging
    assert (session.process, session.address) == (P41, "/tmp/cc-socks/41.sock")
    assert session.replies == (pr.Reply("uds:/tmp/cc-socks/42.sock", "/tmp/cc-socks/42.sock"),)


def test_no_document_or_one_it_cannot_read_is_no_session() -> None:
    failed = pr.session(run=Backbone(code=2, stderr="Error: No such command 'session'."))
    assert not failed.found and "may predate it" in (failed.why or "")
    later = pr.session(run=Backbone(_session_document(schema_version=2)))
    assert not later.found and "schema_version" in (later.why or "")
    untyped = pr.session(run=Backbone(_session_document(found="yes")))
    assert not untyped.found


def test_no_pkit_on_the_path_is_no_session() -> None:
    def missing(argv: list[str], **_options: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(argv[0])

    assert pr.session(run=missing).why == "`pkit` is not on PATH"


def _answers(*states: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "answers": [
            {"name": f"n{i}", "state": state, "by": None, "why": f"why {i}"}
            for i, state in enumerate(states)
        ],
    }


def test_each_name_is_read_in_order_and_passed_whole() -> None:
    backbone = Backbone(_answers(pr.RUNNING, pr.ENDED))
    readings = pr.read([P41, P42], run=backbone)
    assert backbone.calls == [
        (["pkit", "recorded-process", "read", "--json"], {"names": [P41, P42]})
    ]
    assert [(r.runs, r.ended) for r in readings] == [(True, False), (False, True)]
    assert pr.read([], run=backbone) == [] and len(backbone.calls) == 1


def test_a_reading_it_cannot_take_is_cannot_tell_for_every_name() -> None:
    for backbone in (
        Backbone(code=1),
        Backbone(_answers(pr.RUNNING)),
        Backbone({"schema_version": 2, "answers": []}),
    ):
        readings = pr.read([P41, P42], run=backbone)
        assert [r.state for r in readings] == [pr.CANNOT_TELL, pr.CANNOT_TELL]


def test_a_state_it_does_not_know_is_cannot_tell() -> None:
    (reading,) = pr.read([P41], run=Backbone(_answers("paused")))
    assert reading.state == pr.CANNOT_TELL and "paused" in reading.why


def test_two_names_are_compared_by_the_backbone() -> None:
    document = {
        "schema_version": 1,
        "pairs": [{"names": [P41, P41], "answer": pr.ONE, "why": "one"}],
    }
    backbone = Backbone(document)
    assert pr.compare(P41, P41, run=backbone) == pr.ONE
    assert backbone.calls == [
        (["pkit", "recorded-process", "compare", "--json"], {"pairs": [[P41, P41]]})
    ]
    unknown = {**document, "pairs": [{"names": [P41, P41], "answer": "both", "why": "?"}]}
    assert pr.compare(P41, P41, run=Backbone(unknown)) == pr.CANNOT_TELL
    assert pr.compare(P41, P41, run=Backbone(code=1)) == pr.CANNOT_TELL
