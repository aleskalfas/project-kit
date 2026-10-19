"""Tests for `_lib/agent_runs.py`: how project-management starts an agent (ADR-066; #1742).

A capability asks the backbone's run command, `pkit agents run`, and never a
harness. These tests run the real subprocess against a fake `pkit` on PATH:
what pm asks (the agent, the folder, the limit, the effort, `--json`, the brief
on standard input); how the backbone's document reads, and that one pm cannot
read is a run with no answer; a backbone without the command, and no `pkit` at
all; and a `pkit` past pm's bound asked to stop before it is killed. One round
trip runs the backbone's real command, through the claude-code adapter's
runner, under a fake `claude`.
"""

from __future__ import annotations

import json
import os
import signal
import stat
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

from tests.adopter_repo import MakeAdopterRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


@pytest.fixture(scope="module")
def ar() -> ModuleType:
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import agent_runs

    return agent_runs


# A `pkit` that logs how it was asked and what it read on standard input, then
# writes what the test put in FAKE_PKIT_ANSWER: its `stderr`, its `stdout`, and
# exit `code`. With `linger`, it sleeps instead, and writes a mark when it is
# asked to stop. It listens for the stop before anything else, so a slow start
# under load cannot let the signal end it unmarked.
_FAKE_PKIT = """\
import json, os, signal, sys, time
def stop(signum, frame):
    open(os.environ["FAKE_PKIT_LOG"] + ".stopped", "w").write(str(signum))
    sys.exit(143)
signal.signal(signal.SIGTERM, stop)
brief = sys.stdin.read()
with open(os.environ["FAKE_PKIT_LOG"], "w", encoding="utf-8") as log:
    log.write(json.dumps({"argv": sys.argv[1:], "brief": brief}))
with open(os.environ["FAKE_PKIT_ANSWER"], encoding="utf-8") as fh:
    answer = json.load(fh)
if answer.get("linger"):
    time.sleep(60)
sys.stderr.write(answer.get("stderr", ""))
sys.stdout.write(answer.get("stdout", ""))
sys.exit(answer.get("code", 0))
"""


@pytest.fixture
def fake_pkit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake `pkit` first on PATH; returns the folder its log and answer live in."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pkit = bin_dir / "pkit"
    pkit.write_text(f"#!{sys.executable}\n{_FAKE_PKIT}", encoding="utf-8")
    pkit.chmod(pkit.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_PKIT_LOG", str(tmp_path / "log.json"))
    monkeypatch.setenv("FAKE_PKIT_ANSWER", str(tmp_path / "answer.json"))
    return tmp_path


def _answer(where: Path, **answer: object) -> None:
    (where / "answer.json").write_text(json.dumps(answer), encoding="utf-8")


def _document(**fields: object) -> str:
    document: dict[str, object] = {
        "schema_version": 1,
        "agent": "code-reviewer",
        "runner": "claude-code",
        "ending": "finished",
        "exit_code": 0,
        "output": "the review\n",
        "diagnostics": "",
        "reason": "",
    }
    document.update(fields)
    return json.dumps(document) + "\n"


def test_pm_asks_the_backbones_run_command(ar: ModuleType, fake_pkit: Path) -> None:
    _answer(fake_pkit, stdout=_document())
    run = ar.run_agent(
        "code-reviewer", "Review PR 7.", folder=fake_pkit, limit_seconds=720, effort="low"
    )
    assert run == ar.AgentRun("finished", 0, "the review\n", "", "")
    seen = json.loads((fake_pkit / "log.json").read_text(encoding="utf-8"))
    assert seen["argv"] == [
        "agents",
        "run",
        "code-reviewer",
        "--folder",
        str(fake_pkit),
        "--limit",
        "720",
        "--effort",
        "low",
        "--json",
    ]
    assert seen["brief"] == "Review PR 7."


def test_no_effort_passes_none(ar: ModuleType, fake_pkit: Path) -> None:
    _answer(fake_pkit, stdout=_document())
    ar.run_agent("code-reviewer", "Go.", folder=fake_pkit, limit_seconds=5)
    seen = json.loads((fake_pkit / "log.json").read_text(encoding="utf-8"))
    assert "--effort" not in seen["argv"]


@pytest.mark.parametrize(
    "fields",
    [
        {"ending": "refused", "exit_code": None, "reason": "no runner"},
        {"ending": "timed-out", "exit_code": None, "reason": "past its limit"},
        {"ending": "finished", "exit_code": 3, "diagnostics": "crashed"},
    ],
)
def test_the_document_is_the_run(
    ar: ModuleType, fake_pkit: Path, fields: dict[str, object]
) -> None:
    _answer(fake_pkit, stdout=_document(**fields), code=1)
    run = ar.run_agent("code-reviewer", "Go.", folder=fake_pkit, limit_seconds=5)
    assert run.ending == fields["ending"]
    assert run.exit_code == fields["exit_code"]
    assert run.reason == fields.get("reason", "")
    assert run.diagnostics == fields.get("diagnostics", "")


@pytest.mark.parametrize(
    ("fields", "says"),
    [
        ({"schema_version": 2}, "schema_version 2"),
        ({"ending": "approved"}, "an ending pm does not know"),
        ({"exit_code": None}, "no exit_code"),
        ({"exit_code": "0"}, "not an integer"),
        ({"output": None}, "output that is not a string"),
    ],
)
def test_a_document_pm_cannot_read_is_no_answer(
    ar: ModuleType, fake_pkit: Path, fields: dict[str, object], says: str
) -> None:
    _answer(fake_pkit, stdout=_document(**fields))
    run = ar.run_agent("code-reviewer", "Go.", folder=fake_pkit, limit_seconds=5)
    assert run.ending == ar.NO_ANSWER
    assert says in run.reason


def test_a_backbone_without_the_command_names_the_upgrade(ar: ModuleType, fake_pkit: Path) -> None:
    _answer(fake_pkit, stderr="Error: No such command 'run'.\n", code=2)
    run = ar.run_agent("code-reviewer", "Go.", folder=fake_pkit, limit_seconds=5)
    assert run.ending == ar.NO_ANSWER
    assert "older than project-management needs" in run.reason
    assert "`pkit upgrade`" in run.reason


def test_a_run_with_no_document_names_how_pkit_ended(ar: ModuleType, fake_pkit: Path) -> None:
    _answer(fake_pkit, stderr="Error: not in a project tree.\n", code=1)
    run = ar.run_agent("code-reviewer", "Go.", folder=fake_pkit, limit_seconds=5)
    assert run.ending == ar.NO_ANSWER
    assert run.reason == "`pkit agents run` exited 1: Error: not in a project tree."


def test_no_pkit_on_path_did_not_start(
    ar: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    run = ar.run_agent("code-reviewer", "Go.", folder=tmp_path, limit_seconds=5)
    assert run.ending == ar.NOT_STARTED
    assert "`pkit` is not on PATH" in run.reason


def test_past_its_bound_pkit_is_asked_to_stop(
    ar: ModuleType, fake_pkit: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _answer(fake_pkit, linger=True)
    monkeypatch.setattr(ar, "MARGIN_SECONDS", 2)
    started = time.monotonic()
    run = ar.run_agent("code-reviewer", "Go.", folder=fake_pkit, limit_seconds=1)
    assert time.monotonic() - started < 20
    assert run.ending == ar.NO_ANSWER
    assert "gave no answer within 3 s" in run.reason
    stopped = fake_pkit / "log.json.stopped"
    assert stopped.read_text(encoding="utf-8") == str(int(signal.SIGTERM))


def test_a_round_trip_through_the_backbone_and_the_adapters_runner(
    ar: ModuleType,
    make_adopter_repo: MakeAdopterRepo,
    pkit_on_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = make_adopter_repo().root
    agents = root / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "code-reviewer.md").write_text("---\nname: code-reviewer\n---\n", encoding="utf-8")
    harness_bin = tmp_path / "harness-bin"
    harness_bin.mkdir()
    claude = harness_bin / "claude"
    claude.write_text(
        f"#!{sys.executable}\nimport sys\nbrief = sys.stdin.read()\n"
        "print('Reviewer agent (local, code-reviewer): APPROVED')\nprint(brief)\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)
    monkeypatch.setenv("PATH", f"{harness_bin}{os.pathsep}{os.environ['PATH']}")
    run = ar.run_agent("code-reviewer", "The brief.", folder=root, limit_seconds=30)
    assert run == ar.AgentRun(
        "finished", 0, "Reviewer agent (local, code-reviewer): APPROVED\nThe brief.\n", "", ""
    )
