"""Tests for report context sourcing (ADR-050 / #644): the declared project
name (config key → remote-repo-name fallback, never a path segment) and the
pm-dispatched workstream read."""

from __future__ import annotations

import stat
import time
from pathlib import Path

import pytest

from project_kit import command_runner
from project_kit import report_context as rc
from project_kit.command_runner import CommandRun, Ending
from project_kit.report import kind_marker, parse_report_marker, render_context_line

# --- project name: config key ----------------------------------------


def test_read_project_name_absent_file_and_key(tmp_path: Path) -> None:
    assert rc.read_project_name(tmp_path) is None  # no file at all
    path = rc.project_config_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("other: value\n", encoding="utf-8")
    assert rc.read_project_name(tmp_path) is None  # file without the key
    path.write_text("name: ''\n", encoding="utf-8")
    assert rc.read_project_name(tmp_path) is None  # empty name


def test_read_project_name_reads_declared_key(tmp_path: Path) -> None:
    path = rc.project_config_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("name: trip-planner\n", encoding="utf-8")
    assert rc.read_project_name(tmp_path) == "trip-planner"


def test_write_project_name_creates_and_round_trips(tmp_path: Path) -> None:
    written = rc.write_project_name(tmp_path, "alpha")
    assert written == rc.project_config_path(tmp_path)
    assert rc.read_project_name(tmp_path) == "alpha"


def test_write_project_name_preserves_other_keys(tmp_path: Path) -> None:
    path = rc.project_config_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("other: kept\nname: old\n", encoding="utf-8")
    rc.write_project_name(tmp_path, "new")
    content = path.read_text(encoding="utf-8")
    assert "other: kept" in content
    assert rc.read_project_name(tmp_path) == "new"


# --- project name: remote fallback (never the owner/org) -------------


class _FakeProc:
    def __init__(self, returncode: int = 0, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/some-org/trip-planner.git", "trip-planner"),
        ("https://github.com/some-org/trip-planner", "trip-planner"),
        ("git@github.com:some-org/trip-planner.git", "trip-planner"),
        ("ssh://git@github.com/some-org/trip-planner.git", "trip-planner"),
        ("git@host.example:bare-repo.git", "bare-repo"),
        ("", None),
    ],
)
def test_repo_name_from_url_strips_owner_and_git(url: str, expected) -> None:
    assert rc._repo_name_from_url(url) == expected


def test_git_remote_repo_name_parses_origin(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        rc.subprocess,
        "run",
        lambda cmd, **k: _FakeProc(0, "git@github.com:private-org/widget.git\n"),
    )
    assert rc.git_remote_repo_name(tmp_path) == "widget"  # no org, ever


def test_git_remote_repo_name_none_without_remote(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rc.subprocess, "run", lambda cmd, **k: _FakeProc(128))
    assert rc.git_remote_repo_name(tmp_path) is None


def test_resolve_project_name_prefers_config_over_remote(tmp_path: Path, monkeypatch) -> None:
    rc.write_project_name(tmp_path, "declared")
    monkeypatch.setattr(rc.subprocess, "run", lambda cmd, **k: _FakeProc(0, "o/remote.git\n"))
    assert rc.resolve_project_name(tmp_path) == "declared"


def test_resolve_project_name_never_the_directory_basename(tmp_path: Path, monkeypatch) -> None:
    # The never-source-from-paths pin (ADR-050): with no config and no remote,
    # the name is UNRESOLVED — the directory's own name must never leak in.
    project_dir = tmp_path / "secret-client-project"
    project_dir.mkdir()
    monkeypatch.setattr(rc.subprocess, "run", lambda cmd, **k: _FakeProc(128))
    assert rc.resolve_project_name(project_dir) is None


# --- workstream via the pm dispatcher seam and the bounded runner -----


def _verb(tmp_path: Path, monkeypatch, body: str) -> Path:
    """An executable stand-in for the pm read verb, resolved in place of the
    real one — the lookup itself is the dispatcher's, tested there."""
    from project_kit import dispatcher

    script = tmp_path / "context-workstream.py"
    script.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setattr(dispatcher, "resolve_capability_script", lambda root, cap, cmd: script)
    return script


def test_pm_workstream_runs_the_verb_under_the_context_read_policy(
    tmp_path: Path, monkeypatch
) -> None:
    # Through the shared runner, from the project root, with no arguments and
    # the environment left as it is — the verb asks the tracker.
    script = _verb(tmp_path, monkeypatch, "")
    captured: dict = {}

    def fake_run(script_arg, args, **kwargs):
        captured.update(script=script_arg, args=list(args), **kwargs)
        return CommandRun(Ending.UNPARSABLE, 30, returncode=0, stdout="cli\n")

    monkeypatch.setattr(rc, "run_command", fake_run)
    assert rc.pm_workstream(tmp_path) == "cli"
    assert captured == {"script": script, "args": [], "cwd": tmp_path}


@pytest.mark.parametrize(
    ("printed", "expected"),
    [
        ("print('cli')", "cli"),  # the bare value, not a JSON document
        ("print('42')", "42"),  # read as text even where it parses as JSON
        ("print()", None),  # empty output ⇒ omit
    ],
)
def test_pm_workstream_reads_the_printed_value_as_text(
    tmp_path: Path, monkeypatch, printed: str, expected
) -> None:
    _verb(tmp_path, monkeypatch, printed + "\n")
    assert rc.pm_workstream(tmp_path) == expected


def test_pm_workstream_none_when_capability_or_verb_absent(tmp_path: Path, monkeypatch) -> None:
    from project_kit import dispatcher

    monkeypatch.setattr(dispatcher, "resolve_capability_script", lambda root, cap, cmd: None)

    def explode(*args, **kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("no command should run when the verb is absent")

    monkeypatch.setattr(rc, "run_command", explode)
    assert rc.pm_workstream(tmp_path) is None


@pytest.mark.parametrize(
    "body",
    [
        "import sys\nprint('x')\nsys.exit(1)\n",  # non-zero exit ⇒ omit
        "import sys\nsys.exit(2)\n",  # the un-bootstrapped refusal ⇒ omit
        "import sys\nsys.stdout.buffer.write(b'\\xff\\n')\n",  # not UTF-8 ⇒ omit
    ],
)
def test_pm_workstream_none_on_failure_silently(
    tmp_path: Path, monkeypatch, capsys, body: str
) -> None:
    _verb(tmp_path, monkeypatch, body)
    assert rc.pm_workstream(tmp_path) is None
    assert capsys.readouterr().err == ""  # an ordinary miss degrades to silence


def test_pm_workstream_none_when_the_verb_cannot_start(tmp_path: Path, monkeypatch) -> None:
    script = _verb(tmp_path, monkeypatch, "print('cli')\n")
    script.chmod(stat.S_IRUSR | stat.S_IWUSR)  # no longer executable
    assert rc.pm_workstream(tmp_path) is None


def test_pm_workstream_stops_a_hung_verb_at_the_bound_and_says_so(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    _verb(tmp_path, monkeypatch, "import time\ntime.sleep(60)\n")
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    started = time.monotonic()
    assert rc.pm_workstream(tmp_path) is None
    assert time.monotonic() - started < 15  # not the verb's sixty seconds
    err = capsys.readouterr().err
    assert "workstream omitted" in err
    assert "did not answer within 1 s" in err


# --- rendering helpers (pure) ----------------------------------------


def test_render_context_line_all_shapes() -> None:
    assert render_context_line("alpha", "cli") == "Project: alpha · Workstream: cli"
    assert render_context_line("alpha", None) == "Project: alpha"
    assert render_context_line(None, "cli") == "Workstream: cli · (project: not declared)"
    assert render_context_line(None, None) == "(project: not declared)"


def test_kind_marker_context_keys_round_trip() -> None:
    marker = kind_marker("bug", project="alpha", workstream="cli")
    assert parse_report_marker(marker) == {
        "kind": "bug",
        "project": "alpha",
        "workstream": "cli",
    }
    assert parse_report_marker(kind_marker("bug")) == {"kind": "bug"}


def test_kind_marker_tokenizes_whitespace_in_values() -> None:
    # The marker format is space-separated key=value pairs, so a name with
    # spaces is tokenised (the human context line keeps it verbatim).
    marker = kind_marker("feedback", project="My Project")
    assert parse_report_marker(marker) == {
        "kind": "feedback",
        "project": "My-Project",
    }
