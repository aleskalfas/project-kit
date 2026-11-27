"""The backbone's one reading of a recorded process (ADR-103): its names, whether
each runs, and whether two name one process."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from project_kit import recorded_processes as rp
from tests.fake_processes import FakeSystem

REPO = "github.com/owner/repo"


def _reader(system: FakeSystem, *, id_alone: bool = False, session: int | None = None) -> rp.Reader:
    return rp.Reader(rp.space_of(system.space(), REPO), system.platform, id_alone, session)


def _named(system: FakeSystem, pid: int) -> str:
    named = rp.name(pid, _reader(system), system)
    assert named.name is not None, named.why
    return named.name


def _one(
    name: object, system: FakeSystem, *, id_alone: bool = False, session: int | None = None
) -> rp.Answer:
    (answer,) = rp.read([name], _reader(system, id_alone=id_alone, session=session), system)
    return answer


# ---- names ------------------------------------------------------------------------------------


def test_a_name_holds_the_space_the_id_and_the_start_time():
    system = FakeSystem(entries={42: rp.Entry(True, "100.000001")})
    text = _named(system, 42)
    parsed = rp.parse(text)
    assert parsed is not None
    assert text.startswith(f"{rp.FORM}:")
    assert parsed.pid == 42
    assert parsed.start == "100.000001"
    assert parsed.space.namespace == rp.NO_NAMESPACES
    assert "machine-1" not in text
    assert "boot-1" not in text


def test_a_space_is_derived_alike_in_every_clone_and_apart_for_another_repository():
    raw = rp.RawSpace("machine-1", "boot-1", None, False, True)
    assert rp.space_of(raw, REPO) == rp.space_of(raw, REPO)
    assert rp.space_of(raw, REPO).machine != rp.space_of(raw, "github.com/owner/other").machine


def test_no_repository_derives_no_space():
    space = rp.space_of(rp.RawSpace("m", "b", None, False, True), None)
    assert not space.whole
    assert space.why is not None and "origin" in space.why


def test_no_name_where_no_process_holds_the_id_or_it_has_exited():
    system = FakeSystem(entries={7: rp.Entry(True, "1.0", exited=True)})
    assert rp.name(42, _reader(system), system).name is None
    assert rp.name(7, _reader(system), system).name is None


def test_a_start_time_that_cannot_be_read_is_left_out_where_a_signal_finds_the_process():
    system = FakeSystem(entries={42: rp.Entry(None, why="denied")}, signals={42: rp.FOUND})
    parsed = rp.parse(_named(system, 42))
    assert parsed is not None and parsed.start is None


def test_no_name_where_the_own_space_does_not_read_whole():
    system = FakeSystem(
        raw=rp.RawSpace("m", None, None, False, False, "kern.bootsessionuuid: not permitted"),
        entries={42: rp.Entry(True, "1.0")},
    )
    named = rp.name(42, _reader(system), system)
    assert named.name is None
    assert named.why is not None and "not permitted" in named.why


@pytest.mark.parametrize("pid", [0, -1, rp.MAX_PID + 1])
def test_no_id_that_would_reach_a_group_of_processes_is_read(pid: int):
    system = FakeSystem()
    assert rp.name(pid, _reader(system), system).name is None
    assert rp.null_signal(pid) == rp.FAILED


@pytest.mark.parametrize(
    "text",
    [
        "",
        "p2:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:1:2",
        "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:0:2",
        "p1:xyz:bbbbbbbbbbbbbbbb:-:1:2",
        "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:1:2:3",
        "p1:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb:-:1:12:30",
        42,
        None,
    ],
)
def test_no_name_of_a_form_this_reads_is_none(text: object):
    assert rp.parse(text) is None


# ---- reading ----------------------------------------------------------------------------------


def test_running_where_the_process_under_the_id_started_when_it_was_named():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    answer = _one(_named(system, 42), system)
    assert (answer.state, answer.by) == (rp.RUNNING, rp.BY_START_TIME)


def test_ended_where_no_process_holds_the_id():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    system.entries.clear()
    assert (_one(name, system).state, _one(name, system).by) == (rp.ENDED, rp.BY_START_TIME)


def test_ended_where_another_process_took_the_id():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    system.entries[42] = rp.Entry(True, "200.0")
    assert _one(name, system).state == rp.ENDED


def test_ended_where_the_process_has_exited_and_waits_to_be_collected():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    system.entries[42] = rp.Entry(True, "100.0", exited=True)
    assert _one(name, system).state == rp.ENDED


def test_a_start_time_that_cannot_be_read_is_never_taken_for_a_process_that_does_not_run():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    system.entries[42] = rp.Entry(None, why="Operation not permitted")
    system.signals[42] = rp.NONE
    answer = _one(name, system)
    assert answer.state == rp.CANNOT_TELL
    assert "Operation not permitted" in answer.why


def test_a_record_with_no_start_time_runs_only_by_the_id_alone():
    system = FakeSystem(entries={42: rp.Entry(None, why="denied")}, signals={42: rp.FOUND})
    name = _named(system, 42)
    system.entries[42] = rp.Entry(True, "100.0")
    undeclared = _one(name, system)
    assert undeclared.state == rp.CANNOT_TELL
    assert "no start time" in undeclared.why
    system.signals[9] = rp.FOUND
    declared = _one(name, system, id_alone=True, session=9)
    assert (declared.state, declared.by) == (rp.RUNNING, rp.BY_ID_ALONE)


def test_by_the_id_alone_only_once_the_signal_finds_the_own_session():
    system = FakeSystem(entries={42: rp.Entry(None, why="denied")}, signals={42: rp.FOUND})
    name = _named(system, 42)
    assert _one(name, system, id_alone=True, session=None).state == rp.CANNOT_TELL
    hidden = _one(name, system, id_alone=True, session=9)
    assert hidden.state == rp.CANNOT_TELL
    assert "own session" in hidden.why
    system.signals.update({9: rp.FOUND, 42: rp.NONE})
    ended = _one(name, system, id_alone=True, session=9)
    assert (ended.state, ended.by) == (rp.ENDED, rp.BY_ID_ALONE)


def test_another_space_of_the_same_boot_cannot_tell():
    system = FakeSystem(
        platform="linux",
        raw=rp.RawSpace("m", "b", "pid:[1]", True, False),
        entries={42: rp.Entry(True, "5")},
    )
    name = _named(system, 42)
    system.raw = rp.RawSpace("m", "b", "pid:[2]", True, False)
    system.entries.clear()
    answer = _one(name, system)
    assert answer.state == rp.CANNOT_TELL
    assert "another process space" in answer.why


def test_another_machine_cannot_tell():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    system.raw = rp.RawSpace("machine-2", "boot-9", None, False, True)
    assert _one(name, system).state == rp.CANNOT_TELL


def test_an_earlier_boot_of_a_machine_named_once_has_ended():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    system.raw = rp.RawSpace("machine-1", "boot-2", None, False, True)
    answer = _one(name, system)
    assert (answer.state, answer.by) == (rp.ENDED, rp.BY_EARLIER_BOOT)


def test_an_earlier_boot_of_a_machine_whose_identity_may_repeat_cannot_tell():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    system.raw = rp.RawSpace("machine-1", "boot-2", None, False, False)
    assert _one(name, system).state == rp.CANNOT_TELL


def test_every_answer_cannot_tell_where_the_own_space_does_not_read_whole():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    system.raw = rp.RawSpace("machine-1", None, None, False, True, "boot: denied")
    system.entries.clear()
    assert _one(name, system).state == rp.CANNOT_TELL


def test_a_name_with_part_of_its_space_left_out_cannot_tell():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    machine, boot, *_ = _named(system, 42).split(":")[1:]
    assert _one(f"p1:{machine}::-:42:100.0", system).state == rp.CANNOT_TELL
    assert boot


# ---- comparing --------------------------------------------------------------------------------


def test_one_process_two_names():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0"), 43: rp.Entry(True, "100.0")})
    a = _named(system, 42)
    bare = a.rsplit(":", 1)[0] + ":"
    assert rp.compare(a, a).answer == rp.ONE
    assert rp.compare(a, bare).answer == rp.ONE
    assert rp.compare(a, _named(system, 43)).answer == rp.TWO
    assert rp.compare(a, a.rsplit(":", 1)[0] + ":200.0").answer == rp.TWO
    assert rp.compare(a, "nonsense").answer == rp.CANNOT_TELL


# ---- the documents ----------------------------------------------------------------------------


def test_the_documents_answer_each_in_order_and_refuse_a_request_of_another_form():
    system = FakeSystem(entries={42: rp.Entry(True, "100.0")})
    name = _named(system, 42)
    document = rp.read_document({"names": [name, "x"]}, _reader(system), system)
    assert document["schema_version"] == 1
    assert [a["state"] for a in document["answers"]] == [rp.RUNNING, rp.CANNOT_TELL]
    assert rp.compare_document({"pairs": [[name, name]]})["pairs"][0]["answer"] == rp.ONE
    with pytest.raises(rp.FormError):
        rp.read_document({"names": "x"}, _reader(system), system)
    with pytest.raises(rp.FormError):
        rp.compare_document({"pairs": [[name]]})
    with pytest.raises(rp.FormError):
        rp.compare_document([])
    with pytest.raises(rp.FormError):
        rp.read_document({"names": [name, 42]}, _reader(system), system)
    with pytest.raises(rp.FormError):
        rp.compare_document({"pairs": [[name, None]]})


def test_the_repository_is_the_origin_alike_over_ssh_and_https(tmp_path: Path):
    def origin(url: str) -> str | None:
        folder = tmp_path / str(abs(hash(url)))
        folder.mkdir()
        subprocess.run(["git", "init", "-q", str(folder)], check=True)
        subprocess.run(["git", "-C", str(folder), "remote", "add", "origin", url], check=True)
        return rp.repository(folder)

    assert origin("git@github.com:Owner/Repo.git") == origin("https://github.com/owner/repo")
    bare = tmp_path / "none"
    bare.mkdir()
    subprocess.run(["git", "init", "-q", str(bare)], check=True)
    assert rp.repository(bare) is None


# ---- this machine -----------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform not in ("darwin", "linux"), reason="read on macOS and Linux")
def test_this_command_names_and_reads_its_own_process():
    system = rp.this_system()
    raw = system.space()
    if raw.boot is None or raw.machine is None:
        pytest.skip(f"this command reads no whole process space here: {raw.why}")
    reader = rp.Reader(rp.space_of(raw, REPO), system.platform)
    named = rp.name(os.getpid(), reader, system)
    assert named.name is not None, named.why
    (answer,) = rp.read([named.name], reader, system)
    assert (answer.state, answer.by) == (rp.RUNNING, rp.BY_START_TIME)
    assert rp.name(os.getpid(), reader, system).name == named.name


def test_the_commands_answer_on_standard_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from click.testing import CliRunner

    from project_kit.cli import main

    (tmp_path / ".pkit").mkdir()
    (tmp_path / ".pkit" / "manifest.yaml").write_text(
        "backbone_version: 0.0.0\ncomponents: []\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    read = runner.invoke(main, ["recorded-process", "read", "--json"], input='{"names": ["x"]}')
    assert read.exit_code == 0, read.output
    assert json.loads(read.output)["answers"][0]["state"] == rp.CANNOT_TELL
    refused = runner.invoke(main, ["recorded-process", "compare", "--json"], input="nope")
    assert refused.exit_code == 1
    assert "no JSON" in refused.output
