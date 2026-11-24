"""The adapter's declaration of a session, and the session a command finds through
it (ADR-100 point 9, ADR-103 point 5)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import harness_session as hs
from project_kit import recorded_processes as rp
from tests.fake_processes import FakeSystem

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_CODE = ROOT / ".pkit" / "adapters" / "claude-code" / hs.DECLARATION

DECLARED = """\
schema_version: 1
process:
  variable: HARNESS_PID
messaging:
  variable: HARNESS_SOCKET
  reply_prefix: "uds:"
  names_process: '/tmp/socks/(?P<pid>[1-9][0-9]*)\\.sock'
id_alone_platforms: [linux]
"""

ENV = {"HARNESS_PID": "42", "HARNESS_SOCKET": "/tmp/socks/42.sock"}


def _project(tmp_path: Path, declarations: dict[str, str | None]) -> Path:
    root = tmp_path / "proj"
    (root / ".pkit").mkdir(parents=True)
    components = "".join(
        f"  - kind: adapter\n    name: {name}\n"
        f"    manifest: .pkit/adapters/{name}/project/manifest.yaml\n"
        for name in declarations
    )
    registry = components or "  []\n"
    (root / ".pkit" / "manifest.yaml").write_text(
        f"backbone_version: 0.0.0\ncomponents:\n{registry}", encoding="utf-8"
    )
    for name, text in declarations.items():
        folder = root / ".pkit" / "adapters" / name
        folder.mkdir(parents=True)
        if text is not None:
            (folder / hs.DECLARATION).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "https://github.com/o/r"], check=True
    )
    return root


def _live(pid: int = 42) -> FakeSystem:
    return FakeSystem(entries={pid: rp.Entry(True, "100.0")}, signals={pid: rp.FOUND})


# ---- the declaration --------------------------------------------------------------------------


def test_the_claude_code_adapter_declares_its_session():
    declared = hs.parse("claude-code", YAML(typ="safe").load(CLAUDE_CODE.read_text()))
    assert declared.process_variable == "CLAUDE_PID"
    assert declared.address_variable == "CLAUDE_CODE_MESSAGING_SOCKET"
    assert declared.names_process is not None
    assert declared.names_process.fullmatch("/tmp/cc-socks/48754.sock")
    assert not declared.names_process.fullmatch("/Users/someone/cc-socks/48754.sock")
    assert declared.id_alone_platforms == ()


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (lambda d: {**d, "schema_version": 2}, "schema_version"),
        (lambda d: {**d, "extra": 1}, "extra"),
        (lambda d: {**d, "process": {}}, "process.variable"),
        (lambda d: {**d, "process": {"variable": "lower"}}, "environment variable"),
        (
            lambda d: {**d, "messaging": {**d["messaging"], "names_process": "/tmp/x"}},
            "group `pid`",
        ),
        (lambda d: {**d, "messaging": {**d["messaging"], "names_process": "("}}, "no pattern"),
        (lambda d: {**d, "id_alone_platforms": ["Mac OS"]}, "platform"),
    ],
)
def test_a_declaration_of_another_form_is_refused(
    change: Callable[[dict[str, Any]], object], said: str
):
    document = YAML(typ="safe").load(DECLARED)
    with pytest.raises(hs.DeclarationError, match=said):
        hs.parse("h", change(document))


def test_a_harness_with_no_messaging_declares_only_its_process(tmp_path: Path):
    declared = hs.parse("h", {"schema_version": 1, "process": {"variable": "H_PID"}})
    assert declared.address_variable is None
    root = _project(tmp_path, {"h": "schema_version: 1\nprocess:\n  variable: H_PID\n"})
    session = hs.read(root, {"H_PID": "42"}, _live())
    assert session.found and not session.messaging and session.address is None
    assert hs.reply(hs.Found(declared), "uds:/tmp/x").address is None


def test_the_one_registered_adapter_that_declares_a_session_is_read(tmp_path: Path):
    root = _project(tmp_path, {"h": DECLARED, "other": None})
    found = hs.declaration(root)
    assert found.declaration is not None and found.declaration.adapter == "h"


@pytest.mark.parametrize(
    ("declarations", "said"),
    [
        ({}, "no registered adapter"),
        ({"h": DECLARED, "g": DECLARED}, "more than one"),
        ({"h": "schema_version: 1\n"}, "cannot be read"),
    ],
)
def test_no_declaration_where_none_one_cannot_be_read_or_two_are(
    tmp_path: Path, declarations: dict[str, str | None], said: str
):
    found = hs.declaration(_project(tmp_path, declarations))
    assert found.declaration is None
    assert found.why is not None and said in found.why


# ---- the session ------------------------------------------------------------------------------


def test_the_session_its_process_and_its_address(tmp_path: Path):
    root = _project(tmp_path, {"h": DECLARED})
    session = hs.read(root, ENV, _live())
    assert session.found and session.messaging
    assert session.address == "/tmp/socks/42.sock"
    assert session.process is not None
    parsed = rp.parse(session.process)
    assert parsed is not None and parsed.pid == 42
    document = session.document()
    assert document["schema_version"] == 1
    assert set(document) == {
        "schema_version",
        "adapter",
        "found",
        "why",
        "messaging",
        "process",
        "process_why",
        "address",
        "address_why",
        "replies",
    }


def test_no_session_where_the_variable_names_no_process(tmp_path: Path):
    root = _project(tmp_path, {"h": DECLARED})
    session = hs.read(root, {}, _live())
    assert not session.found
    assert session.why is not None and "HARNESS_PID" in session.why
    assert session.process is None and session.address is None


def test_no_process_and_no_address_where_a_signal_does_not_find_the_process(tmp_path: Path):
    root = _project(tmp_path, {"h": DECLARED})
    session = hs.read(root, ENV, FakeSystem(entries={42: rp.Entry(True, "1.0")}))
    assert session.found
    assert session.process is None and session.address is None
    assert session.process_why is not None and "null signal" in session.process_why


@pytest.mark.parametrize("address", ["/tmp/socks/43.sock", "/home/someone/42.sock", ""])
def test_no_address_where_it_does_not_name_the_sessions_process(tmp_path: Path, address: str):
    root = _project(tmp_path, {"h": DECLARED})
    session = hs.read(root, {**ENV, "HARNESS_SOCKET": address}, _live())
    assert session.process is not None
    assert session.address is None
    assert session.address_why is not None


def test_a_reply_address_is_brought_into_the_addresss_form(tmp_path: Path):
    root = _project(tmp_path, {"h": DECLARED})
    session = hs.read(
        root, ENV, _live(), replies=("uds:/tmp/socks/9.sock", "/tmp/socks/9.sock", "uds:/x")
    )
    assert [r.address for r in session.replies] == ["/tmp/socks/9.sock", None, None]


def test_the_reader_reads_by_the_id_alone_only_on_a_declared_platform(tmp_path: Path):
    root = _project(tmp_path, {"h": DECLARED})
    found = hs.declaration(root)
    assert not hs.reader(root, found, ENV, FakeSystem(platform="darwin")).id_alone
    linux = hs.reader(root, found, ENV, FakeSystem(platform="linux"))
    assert linux.id_alone
    assert linux.session_pid == 42
    assert linux.space.whole
