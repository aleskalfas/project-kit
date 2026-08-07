"""Tests for the `pkit report` composition logic (PRJ-008 / ADR-047)."""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import pytest

from project_kit.report import (
    KINDS,
    REPORT_TARGET,
    build_new_issue_url,
    compose_report,
    compose_report_body,
)


def test_compose_report_body_includes_prose_and_env() -> None:
    body = compose_report_body(
        "Something broke on upgrade.",
        "## Environment\n\n```\nbackbone:      1.143.1\n```\n",
    )
    assert "Something broke on upgrade." in body
    assert "## Environment" in body
    assert "backbone:      1.143.1" in body
    assert "Reported for" not in body


def test_compose_report_body_attribution_normalizes_handle() -> None:
    body = compose_report_body("prose", "## Environment\n", on_behalf_of="@mike")
    assert "Reported for @mike" in body
    assert "@@mike" not in body  # leading @ stripped, not doubled


def test_build_new_issue_url_encodes_params() -> None:
    url = build_new_issue_url(
        "owner/repo", title="Bug: sandbox", body="line1\nline2", label="bug"
    )
    assert url.startswith("https://github.com/owner/repo/issues/new?")
    q = urllib.parse.parse_qs(url.split("?", 1)[1])
    assert q["title"] == ["Bug: sandbox"]
    assert q["body"] == ["line1\nline2"]
    assert q["labels"] == ["bug"]


def test_compose_report_ties_env_and_url(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    body, url = compose_report("bug", title="T", prose="P", target_root=tmp_path)
    assert "## Environment" in body
    assert "P" in body
    assert REPORT_TARGET in url
    assert "issues/new?" in url


def test_compose_report_feedback_kind_labels_feedback(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    _, url = compose_report("feedback", title="T", prose="P", target_root=tmp_path)
    q = urllib.parse.parse_qs(url.split("?", 1)[1])
    assert q["labels"] == ["feedback"]


def test_compose_report_unknown_kind_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        compose_report("nope", title="T", prose="P", target_root=tmp_path)


def test_kinds_are_bug_and_feedback() -> None:
    assert set(KINDS) == {"bug", "feedback"}


# --- CLI (URL-first path) --------------------------------------------

from click.testing import CliRunner  # noqa: E402

from project_kit.cli import main  # noqa: E402


def test_cli_report_bug_prints_prefilled_url() -> None:
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "sandbox bug", "--body", "it broke"]
    )
    assert res.exit_code == 0, res.output
    assert f"issues/new?" in res.output
    assert REPORT_TARGET in res.output
    assert "labels=bug" in res.output
    assert "environment block" in res.output.lower()


def test_cli_report_feedback_labels_feedback() -> None:
    res = CliRunner().invoke(
        main, ["report", "feedback", "--title", "t", "--body", "some thoughts"]
    )
    assert res.exit_code == 0, res.output
    assert "labels=feedback" in res.output


def test_cli_report_no_subcommand_shows_usage() -> None:
    res = CliRunner().invoke(main, ["report"])
    assert res.exit_code == 0
    assert "report bug|feedback" in res.output


# --- gh-auto-file path (mocked gh) -----------------------------------

import project_kit.report as rep  # noqa: E402


class _FakeProc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_file_report_via_gh_argv_and_success(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeProc(0, "https://github.com/owner/repo/issues/99\n")

    monkeypatch.setattr(rep.subprocess, "run", fake_run)
    url = rep.file_report_via_gh("owner/repo", title="T", body="B", label="bug")
    assert url == "https://github.com/owner/repo/issues/99"
    assert captured["cmd"][:5] == ["gh", "issue", "create", "--repo", "owner/repo"]
    assert "--label" in captured["cmd"] and "bug" in captured["cmd"]


def test_file_report_via_gh_failure_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(rep.subprocess, "run", lambda cmd, **k: _FakeProc(1, "", "boom"))
    assert rep.file_report_via_gh("o/r", title="T", body="B", label="bug") is None


def test_gh_authenticated_false_when_gh_absent(monkeypatch) -> None:
    monkeypatch.setattr(rep.shutil, "which", lambda _name: None)
    assert rep.gh_authenticated() is False


def test_cli_file_yes_degrades_and_does_not_post(monkeypatch) -> None:
    # --file --yes must NEVER auto-post the foreign write (ADR-047) — degrade to URL.
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--file", "--yes"]
    )
    assert res.exit_code == 0
    assert posted["v"] is False
    assert "issues/new?" in res.output
    assert "ADR-047" in res.output


def test_cli_file_confirm_yes_posts(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda target, **k: "https://github.com/aleskalfas/project-kit/issues/700",
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--file"], input="y\n"
    )
    assert res.exit_code == 0, res.output
    assert "filed:" in res.output and "700" in res.output


def test_cli_file_decline_degrades(monkeypatch) -> None:
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--file"], input="n\n"
    )
    assert res.exit_code == 0
    assert posted["v"] is False
    assert "Not posted" in res.output and "issues/new?" in res.output


def test_cli_file_no_auth_degrades(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", lambda: False)
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--file"]
    )
    assert res.exit_code == 0
    assert "not authenticated" in res.output and "issues/new?" in res.output


# --- tracking reads --------------------------------------------------


def test_parse_tracked_by() -> None:
    body = "prose\n\n## Tracked by\n\n- [ ] #123\n- [x] #145\n\n## Other\n#999\n"
    assert rep.parse_tracked_by(body) == [123, 145]  # stops at the next heading
    assert rep.parse_tracked_by("no section, incidental #5") == []
    assert rep.parse_tracked_by("## Tracked by\n- [ ] #7\n- [ ] #7\n") == [7]  # de-dup


def test_display_state() -> None:
    assert rep.display_state("CLOSED", []) == "closed"
    assert rep.display_state("OPEN", ["state:in-progress"]) == "in progress"
    assert rep.display_state("open", ["type:bug"]) == "open"


def test_list_my_reports_filters_to_bug_feedback_and_sorts(monkeypatch) -> None:
    issues = [
        {"number": 1, "title": "a bug", "state": "OPEN",
         "labels": [{"name": "bug"}], "updatedAt": "2026-08-01"},
        {"number": 2, "title": "not a report", "state": "OPEN",
         "labels": [{"name": "docs"}], "updatedAt": "2026-08-05"},
        {"number": 3, "title": "some feedback", "state": "CLOSED",
         "labels": [{"name": "feedback"}], "updatedAt": "2026-08-03"},
    ]
    monkeypatch.setattr(rep, "_gh_json", lambda args: issues)
    reports = rep.list_my_reports("o/r")
    assert [r.number for r in reports] == [3, 1]  # #2 dropped; newest-first
    assert reports[0].state == "closed" and reports[0].kind == "feedback"


def test_list_my_reports_gh_failure_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(rep, "_gh_json", lambda args: None)
    assert rep.list_my_reports("o/r") is None


def test_show_report_resolves_tracked_by(monkeypatch) -> None:
    def fake_gh_json(args):
        n = args[3]
        if n == "42":
            return {
                "number": 42, "title": "fb", "state": "OPEN",
                "body": "p\n\n## Tracked by\n- [ ] #7\n",
                "labels": [{"name": "feedback"}],
                "comments": [{"body": "working on it"}],
            }
        if n == "7":
            return {"state": "CLOSED", "labels": []}
        return None

    monkeypatch.setattr(rep, "_gh_json", fake_gh_json)
    detail = rep.show_report("o/r", 42)
    assert detail["state"] == "open" and detail["kind"] == "feedback"
    assert detail["tracked_by"] == {7: "closed"}
    assert len(detail["comments"]) == 1


def test_cli_report_list(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "list_my_reports",
        lambda target: [rep.ReportSummary(1, "a bug", "bug", "open", "2026-08-01")],
    )
    res = CliRunner().invoke(main, ["report"])
    assert res.exit_code == 0
    assert "#1" in res.output and "a bug" in res.output


def test_list_my_reports_tree_pairs_each_with_tracked(monkeypatch) -> None:
    def fake_gh_json(args):
        if "list" in args:
            return [{
                "number": 42, "title": "fb", "state": "OPEN",
                "labels": [{"name": "feedback"}], "updatedAt": "2026-08-03",
                "body": "p\n\n## Tracked by\n- [ ] #7\n",
            }]
        if args[3] == "7":
            return {"state": "CLOSED", "labels": []}
        return None

    monkeypatch.setattr(rep, "_gh_json", fake_gh_json)
    rows = rep.list_my_reports_tree("o/r")
    assert len(rows) == 1
    summary, tracked = rows[0]
    assert summary.number == 42 and tracked == {7: "closed"}


def test_cli_report_tree(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "list_my_reports_tree",
        lambda target: [(
            rep.ReportSummary(42, "fb", "feedback", "open", "2026-08-03"),
            {7: "closed"},
        )],
    )
    res = CliRunner().invoke(main, ["report", "--tree"])
    assert res.exit_code == 0
    assert "#42" in res.output and "#7" in res.output and "closed" in res.output


def test_cli_report_list_no_auth_degrades(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", lambda: False)
    res = CliRunner().invoke(main, ["report"])
    assert "github.com" in res.output and "auth" in res.output.lower()


def test_cli_report_show(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "show_report",
        lambda t, n: {
            "number": 42, "title": "fb", "state": "open", "kind": "feedback",
            "comments": [{"body": "working on it"}],
            "tracked_by": {7: "closed", 8: "in progress"},
        },
    )
    res = CliRunner().invoke(main, ["report", "show", "42"])
    assert res.exit_code == 0
    assert "#42" in res.output and "Tracked by" in res.output
    assert "#7" in res.output and "maintainer comment" in res.output
