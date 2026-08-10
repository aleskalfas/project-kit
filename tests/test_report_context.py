"""Tests for report context sourcing (ADR-050 / #644): the declared project
name (config key → remote-repo-name fallback, never a path segment) and the
pm-dispatched workstream read."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from project_kit import report_context as rc
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
        rc.subprocess, "run",
        lambda cmd, **k: _FakeProc(0, "git@github.com:private-org/widget.git\n"),
    )
    assert rc.git_remote_repo_name(tmp_path) == "widget"  # no org, ever


def test_git_remote_repo_name_none_without_remote(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rc.subprocess, "run", lambda cmd, **k: _FakeProc(128))
    assert rc.git_remote_repo_name(tmp_path) is None


def test_resolve_project_name_prefers_config_over_remote(
    tmp_path: Path, monkeypatch
) -> None:
    rc.write_project_name(tmp_path, "declared")
    monkeypatch.setattr(
        rc.subprocess, "run", lambda cmd, **k: _FakeProc(0, "o/remote.git\n")
    )
    assert rc.resolve_project_name(tmp_path) == "declared"


def test_resolve_project_name_never_the_directory_basename(
    tmp_path: Path, monkeypatch
) -> None:
    # The never-source-from-paths pin (ADR-050): with no config and no remote,
    # the name is UNRESOLVED — the directory's own name must never leak in.
    project_dir = tmp_path / "secret-client-project"
    project_dir.mkdir()
    monkeypatch.setattr(rc.subprocess, "run", lambda cmd, **k: _FakeProc(128))
    assert rc.resolve_project_name(project_dir) is None


# --- workstream via the pm dispatcher seam ---------------------------


def test_pm_workstream_reads_verb_output(tmp_path: Path, monkeypatch) -> None:
    from project_kit import dispatcher

    script = tmp_path / "context-workstream.py"
    script.write_text("#!/bin/true\n", encoding="utf-8")
    monkeypatch.setattr(
        dispatcher, "resolve_capability_script", lambda root, cap, cmd: script
    )
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = kwargs.get("cwd")
        return _FakeProc(0, "cli\n")

    monkeypatch.setattr(rc.subprocess, "run", fake_run)
    assert rc.pm_workstream(tmp_path) == "cli"
    assert captured["cmd"] == [str(script)]  # dispatched by subprocess
    assert captured["cwd"] == tmp_path


def test_pm_workstream_none_when_capability_or_verb_absent(
    tmp_path: Path, monkeypatch
) -> None:
    from project_kit import dispatcher

    monkeypatch.setattr(
        dispatcher, "resolve_capability_script", lambda root, cap, cmd: None
    )

    def explode(cmd, **kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("no subprocess should run when the verb is absent")

    monkeypatch.setattr(rc.subprocess, "run", explode)
    assert rc.pm_workstream(tmp_path) is None


def test_pm_workstream_none_on_empty_output_or_failure(
    tmp_path: Path, monkeypatch
) -> None:
    from project_kit import dispatcher

    script = tmp_path / "context-workstream.py"
    script.write_text("#!/bin/true\n", encoding="utf-8")
    monkeypatch.setattr(
        dispatcher, "resolve_capability_script", lambda root, cap, cmd: script
    )
    monkeypatch.setattr(rc.subprocess, "run", lambda cmd, **k: _FakeProc(0, "\n"))
    assert rc.pm_workstream(tmp_path) is None  # empty output ⇒ omit
    monkeypatch.setattr(rc.subprocess, "run", lambda cmd, **k: _FakeProc(1, "x"))
    assert rc.pm_workstream(tmp_path) is None  # non-zero exit ⇒ omit


# --- rendering helpers (pure) ----------------------------------------


def test_render_context_line_all_shapes() -> None:
    assert render_context_line("alpha", "cli") == "Project: alpha · Workstream: cli"
    assert render_context_line("alpha", None) == "Project: alpha"
    assert (
        render_context_line(None, "cli")
        == "Workstream: cli · (project: not declared)"
    )
    assert render_context_line(None, None) == "(project: not declared)"


def test_kind_marker_context_keys_round_trip() -> None:
    marker = kind_marker("bug", project="alpha", workstream="cli")
    assert parse_report_marker(marker) == {
        "kind": "bug", "project": "alpha", "workstream": "cli",
    }
    assert parse_report_marker(kind_marker("bug")) == {"kind": "bug"}


def test_kind_marker_tokenizes_whitespace_in_values() -> None:
    # The marker format is space-separated key=value pairs, so a name with
    # spaces is tokenised (the human context line keeps it verbatim).
    marker = kind_marker("feedback", project="My Project")
    assert parse_report_marker(marker) == {
        "kind": "feedback", "project": "My-Project",
    }
