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
    title, body, url = compose_report("bug", title="T", prose="P", target_root=tmp_path)
    assert title == "T"  # bug titles are not prefixed
    assert "## Environment" in body
    assert "P" in body
    assert REPORT_TARGET in url
    assert "issues/new?" in url


def test_compose_report_feedback_kind_labels_feedback(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    _, _, url = compose_report("feedback", title="T", prose="P", target_root=tmp_path)
    q = urllib.parse.parse_qs(url.split("?", 1)[1])
    assert q["labels"] == ["feedback"]


def test_compose_report_unknown_kind_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        compose_report("nope", title="T", prose="P", target_root=tmp_path)


def test_kinds_are_bug_feedback_change_request() -> None:
    assert set(KINDS) == {"bug", "feedback", "change-request"}


def test_compose_report_stamps_kind_marker(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    for kind in KINDS:
        _, body, _ = compose_report(kind, title="T", prose="P", target_root=tmp_path)
        assert f"<!-- pkit-report: kind={kind} -->" in body


# --- change-request kind (compose) -----------------------------------


def test_compose_change_request_prefixes_title_and_templates_body(
    tmp_path: Path,
) -> None:
    (tmp_path / ".pkit").mkdir()
    title, body, url = compose_report(
        "change-request", title="add a flag", prose="I keep retyping it.",
        target_root=tmp_path,
    )
    assert title == "[CR] add a flag"
    assert "### Motivation" in body and "I keep retyping it." in body
    assert "### Desired behaviour" in body and "### Current workaround" in body
    q = urllib.parse.parse_qs(url.split("?", 1)[1])
    assert q["labels"] == ["change-request"]
    assert q["title"] == ["[CR] add a flag"]


def test_compose_change_request_keeps_existing_prefix_and_headings(
    tmp_path: Path,
) -> None:
    prose = "### Motivation\n\nwhy\n\n### Desired behaviour\n\nwhat\n"
    (tmp_path / ".pkit").mkdir()
    title, body, _ = compose_report(
        "change-request", title="[CR] already prefixed", prose=prose,
        target_root=tmp_path,
    )
    assert title == "[CR] already prefixed"  # not doubled
    assert body.count("### Motivation") == 1  # template not re-applied


def test_parse_report_marker() -> None:
    body = "prose\n<!-- pkit-report: kind=change-request -->\n"
    assert rep.parse_report_marker(body) == {"kind": "change-request"}
    multi = "<!-- pkit-report: kind=feedback project=alpha -->"
    assert rep.parse_report_marker(multi) == {"kind": "feedback", "project": "alpha"}
    assert rep.parse_report_marker("no marker here") == {}


def test_classify_kind_label_marker_and_title_prefix() -> None:
    assert rep.classify_kind(["bug"], "[CR] t", "") == "bug"  # label wins
    assert rep.classify_kind([], "t", "<!-- pkit-report: kind=feedback -->") == "feedback"
    assert rep.classify_kind([], "[CR] add a flag", "") == "change-request"
    assert rep.classify_kind([], "unrelated CR mention", "prose") == ""


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


def test_list_my_reports_includes_attributed(monkeypatch) -> None:
    def fake(args):
        if args[:3] == ["gh", "api", "user"]:
            return {"login": "mike"}
        if "--author" in args:
            return [{"number": 1, "title": "mine", "state": "OPEN",
                     "labels": [{"name": "bug"}], "updatedAt": "2026-08-01"}]
        if "--search" in args:
            return [{"number": 9, "title": "for mike", "state": "OPEN",
                     "labels": [{"name": "feedback"}], "updatedAt": "2026-08-05"}]
        return None

    monkeypatch.setattr(rep, "_gh_json", fake)
    reports = rep.list_my_reports("o/r")
    assert [r.number for r in reports] == [9, 1]  # newest first
    assert next(r for r in reports if r.number == 9).attributed is True
    assert next(r for r in reports if r.number == 1).attributed is False


def test_list_my_reports_authored_wins_over_attributed(monkeypatch) -> None:
    # an issue both authored and self-attributed should render as authored.
    def fake(args):
        if args[:3] == ["gh", "api", "user"]:
            return {"login": "mike"}
        issue = {"number": 5, "title": "dual", "state": "OPEN",
                 "labels": [{"name": "bug"}], "updatedAt": "2026-08-02"}
        return [issue]  # both --author and --search return it

    monkeypatch.setattr(rep, "_gh_json", fake)
    reports = rep.list_my_reports("o/r")
    assert [r.number for r in reports] == [5]
    assert reports[0].attributed is False  # authored wins the de-dup


def test_cli_report_list_marks_attributed(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "list_my_reports",
        lambda t: [rep.ReportSummary(
            9, "for mike", "feedback", "open", "2026-08-05", attributed=True
        )],
    )
    res = CliRunner().invoke(main, ["report"])
    assert res.exit_code == 0
    assert "filed for you" in res.output


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


# --- maintainer side (pure body helpers + gated commands) ------------


def test_add_tracked_ref_creates_section_when_absent() -> None:
    out = rep.add_tracked_ref("Some feedback prose.\n", 7)
    assert "## Tracked by" in out and "- [ ] #7" in out


def test_add_tracked_ref_appends_within_existing_section() -> None:
    body = "prose\n\n## Tracked by\n\n- [ ] #7\n\n## Notes\nmore\n"
    out = rep.add_tracked_ref(body, 8)
    assert rep.parse_tracked_by(out) == [7, 8]
    assert "## Notes" in out  # the ref landed in the section, not after Notes


def test_add_tracked_ref_is_idempotent() -> None:
    body = "## Tracked by\n- [ ] #7\n"
    assert rep.add_tracked_ref(body, 7) == body


def test_remove_tracked_ref_drops_the_line_keeps_heading() -> None:
    body = "prose\n\n## Tracked by\n- [ ] #7\n- [x] #8\n"
    out = rep.remove_tracked_ref(body, 7)
    assert rep.parse_tracked_by(out) == [8]
    assert "## Tracked by" in out
    assert rep.remove_tracked_ref(out, 8) == out.replace("- [x] #8\n", "")


def test_in_report_target_gate(monkeypatch) -> None:
    monkeypatch.setattr(rep, "current_repo_slug", lambda: rep.REPORT_TARGET)
    assert rep.in_report_target() is True
    monkeypatch.setattr(rep, "current_repo_slug", lambda: "someone/fork")
    assert rep.in_report_target() is False


def test_list_inbox_dedups_across_labels(monkeypatch) -> None:
    def fake_gh_json(args):
        # both label queries return the same #5 (carries both labels)
        return [{
            "number": 5, "title": "dual", "state": "OPEN",
            "labels": [{"name": "bug"}, {"name": "feedback"}],
            "updatedAt": "2026-08-04",
        }]

    monkeypatch.setattr(rep, "_gh_json", fake_gh_json)
    inbox = rep.list_inbox("o/r")
    assert [r.number for r in inbox] == [5]  # de-duped


def test_link_fix_fetches_edits(monkeypatch) -> None:
    edited = {}

    def fake_gh_json(args):
        return {"body": "prose\n"}  # the issue view

    def fake_edit(target, number, body):
        edited["body"] = body
        return True

    monkeypatch.setattr(rep, "_gh_json", fake_gh_json)
    monkeypatch.setattr(rep, "_edit_body", fake_edit)
    assert rep.link_fix("o/r", 42, 7) is True
    assert "- [ ] #7" in edited["body"]


def test_cli_inbox_gated_outside_target(monkeypatch) -> None:
    monkeypatch.setattr(rep, "in_report_target", lambda: False)
    res = CliRunner().invoke(main, ["report", "inbox"])
    assert res.exit_code != 0
    assert "runs only inside" in res.output


def test_cli_link_inside_target(monkeypatch) -> None:
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    monkeypatch.setattr(rep, "link_fix", lambda t, f, x: True)
    res = CliRunner().invoke(main, ["report", "link", "42", "7"])
    assert res.exit_code == 0
    assert "Linked #7 into #42" in res.output


def test_cli_change_request_prints_prefilled_url() -> None:
    res = CliRunner().invoke(
        main,
        ["report", "change-request", "--title", "add a flag", "--body", "retyping"],
    )
    assert res.exit_code == 0, res.output
    assert "issues/new?" in res.output
    assert "labels=change-request" in res.output
    assert urllib.parse.quote_plus("[CR] add a flag") in res.output


def test_cli_change_request_file_yes_degrades_and_does_not_post(monkeypatch) -> None:
    # same ADR-047 asymmetry as bug/feedback: --file --yes NEVER auto-posts.
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main,
        ["report", "change-request", "--title", "t", "--body", "b", "--file", "--yes"],
    )
    assert res.exit_code == 0
    assert posted["v"] is False
    assert "issues/new?" in res.output and "ADR-047" in res.output


# --- inbox filtering (--kind / --group-by) ---------------------------


_INBOX_ISSUES = [
    {"number": 1, "title": "a bug", "state": "OPEN",
     "labels": [{"name": "bug"}], "updatedAt": "2026-08-01", "body": "b"},
    {"number": 2, "title": "some feedback", "state": "OPEN",
     "labels": [{"name": "feedback"}], "updatedAt": "2026-08-02", "body": "f"},
    {"number": 3, "title": "[CR] unlabelled cr", "state": "OPEN",
     "labels": [], "updatedAt": "2026-08-03",
     "body": "p\n<!-- pkit-report: kind=change-request -->\n"},
    {"number": 4, "title": "mentions CR only", "state": "OPEN",
     "labels": [], "updatedAt": "2026-08-04", "body": "not a report"},
]


def test_list_inbox_kind_filters_and_classifies_unlabelled_cr(monkeypatch) -> None:
    monkeypatch.setattr(rep, "_gh_json", lambda args: _INBOX_ISSUES)
    inbox = rep.list_inbox("o/r", kind="change-request")
    # #3 classifies by marker/prefix despite no label; #4 (search noise) is dropped.
    assert [r.number for r in inbox] == [3]
    inbox_all = rep.list_inbox("o/r")
    assert [r.number for r in inbox_all] == [3, 2, 1]  # newest first, #4 dropped


def test_list_inbox_queries_search_titles_for_cr(monkeypatch) -> None:
    seen: list[list[str]] = []

    def fake(args):
        seen.append(args)
        return []

    monkeypatch.setattr(rep, "_gh_json", fake)
    rep.list_inbox("o/r", kind="change-request")
    assert any("--label" in q and "change-request" in q for q in seen)
    assert any("--search" in q for q in seen)  # discovers label-less URL-filed CRs


def test_cli_inbox_kind_flag(monkeypatch) -> None:
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    captured = {}

    def fake_list(target, *, kind=None):
        captured["kind"] = kind
        return [rep.ReportSummary(3, "[CR] t", "change-request", "open", "2026-08-03")]

    monkeypatch.setattr(rep, "list_inbox", fake_list)
    res = CliRunner().invoke(main, ["report", "inbox", "--kind", "change-request"])
    assert res.exit_code == 0, res.output
    assert captured["kind"] == "change-request"
    assert "#3" in res.output


def test_cli_inbox_group_by_project_degrades_without_marker(monkeypatch) -> None:
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    monkeypatch.setattr(
        rep, "list_inbox",
        lambda target, *, kind=None: [
            rep.ReportSummary(1, "a", "bug", "open", "2026-08-01", project="alpha"),
            rep.ReportSummary(2, "b", "feedback", "open", "2026-08-02"),
        ],
    )
    res = CliRunner().invoke(main, ["report", "inbox", "--group-by", "project"])
    assert res.exit_code == 0, res.output
    assert "alpha" in res.output
    assert "(no project)" in res.output  # markerless reports still render


# --- inbox --resolved (close-prompt) ---------------------------------


def test_list_resolved_requires_all_tracked_closed(monkeypatch) -> None:
    issues = [
        {"number": 10, "title": "all closed", "state": "OPEN",
         "labels": [{"name": "feedback"}], "updatedAt": "2026-08-01",
         "body": "p\n\n## Tracked by\n- [x] #7\n"},
        {"number": 11, "title": "one open", "state": "OPEN",
         "labels": [{"name": "feedback"}], "updatedAt": "2026-08-02",
         "body": "p\n\n## Tracked by\n- [ ] #8\n"},
        {"number": 12, "title": "untracked", "state": "OPEN",
         "labels": [{"name": "feedback"}], "updatedAt": "2026-08-03", "body": "p"},
    ]

    def fake(args):
        if "list" in args:
            return issues
        if args[3] == "7":
            return {"state": "CLOSED", "labels": []}
        if args[3] == "8":
            return {"state": "OPEN", "labels": []}
        return None

    monkeypatch.setattr(rep, "_gh_json", fake)
    rows = rep.list_resolved("o/r")
    assert [(r.number, tracked) for r, tracked in rows] == [(10, [7])]


def test_list_resolved_excludes_bugs_and_closed_reports(monkeypatch) -> None:
    issues = [
        {"number": 20, "title": "a bug", "state": "OPEN",
         "labels": [{"name": "bug"}], "updatedAt": "2026-08-01",
         "body": "p\n\n## Tracked by\n- [x] #7\n"},
        {"number": 21, "title": "already closed", "state": "CLOSED",
         "labels": [{"name": "feedback"}], "updatedAt": "2026-08-02",
         "body": "p\n\n## Tracked by\n- [x] #7\n"},
    ]

    def fake(args):
        if "list" in args:
            return issues
        return {"state": "CLOSED", "labels": []}

    monkeypatch.setattr(rep, "_gh_json", fake)
    assert rep.list_resolved("o/r") == []


def test_close_report_as_resolved_comments_then_closes(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeProc(0)

    monkeypatch.setattr(rep.subprocess, "run", fake_run)
    assert rep.close_report_as_resolved("o/r", 10, [7, 8]) is True
    assert calls[0][:3] == ["gh", "issue", "comment"]
    assert "#7, #8" in calls[0][calls[0].index("--body") + 1]
    assert calls[1][:3] == ["gh", "issue", "close"]


_RESOLVED_ROW = (
    rep.ReportSummary(10, "all closed", "feedback", "open", "2026-08-01"),
    [7],
)


def test_cli_inbox_resolved_yes_lists_but_never_closes(monkeypatch) -> None:
    closed = {"v": False}
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    monkeypatch.setattr(rep, "list_resolved", lambda target: [_RESOLVED_ROW])
    monkeypatch.setattr(
        rep, "close_report_as_resolved",
        lambda *a, **k: closed.__setitem__("v", True) or True,
    )
    res = CliRunner().invoke(main, ["report", "inbox", "--resolved", "--yes"])
    assert res.exit_code == 0, res.output
    assert closed["v"] is False  # --yes lists only — the close needs a live confirm
    assert "#10" in res.output and "listing only" in res.output


def test_cli_inbox_resolved_no_input_never_closes(monkeypatch) -> None:
    # non-interactive without --yes: the confirm aborts on EOF; nothing closes.
    closed = {"v": False}
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    monkeypatch.setattr(rep, "list_resolved", lambda target: [_RESOLVED_ROW])
    monkeypatch.setattr(
        rep, "close_report_as_resolved",
        lambda *a, **k: closed.__setitem__("v", True) or True,
    )
    res = CliRunner().invoke(main, ["report", "inbox", "--resolved"])
    assert closed["v"] is False
    assert res.exit_code != 0  # aborted at the confirm, after listing


def test_cli_inbox_resolved_confirm_closes(monkeypatch) -> None:
    calls: list[tuple] = []
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    monkeypatch.setattr(rep, "list_resolved", lambda target: [_RESOLVED_ROW])
    monkeypatch.setattr(
        rep, "close_report_as_resolved",
        lambda t, n, tracked: calls.append((n, tracked)) or True,
    )
    res = CliRunner().invoke(main, ["report", "inbox", "--resolved"], input="y\n")
    assert res.exit_code == 0, res.output
    assert calls == [(10, [7])]
    assert "Closed #10" in res.output


def test_cli_inbox_resolved_decline_skips(monkeypatch) -> None:
    closed = {"v": False}
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    monkeypatch.setattr(rep, "list_resolved", lambda target: [_RESOLVED_ROW])
    monkeypatch.setattr(
        rep, "close_report_as_resolved",
        lambda *a, **k: closed.__setitem__("v", True) or True,
    )
    res = CliRunner().invoke(main, ["report", "inbox", "--resolved"], input="n\n")
    assert res.exit_code == 0, res.output
    assert closed["v"] is False
    assert "Skipped #10" in res.output


def test_cli_inbox_resolved_rejects_kind_combination(monkeypatch) -> None:
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    res = CliRunner().invoke(
        main, ["report", "inbox", "--resolved", "--kind", "bug"]
    )
    assert res.exit_code != 0
    assert "does not combine" in res.output


# --- scratchpad attachment compose helpers (COR-043 / ADR-047) -------


def test_lint_redaction_flags_home_paths() -> None:
    text = (
        "clean line\n"
        "ref to $HOME/config\n"
        "path /Users/alice/project\n"
        "path /home/bob/project\n"
        "rel ~/notes.md\n"
    )
    findings = rep.lint_redaction(text)
    assert [f.line for f in findings] == [2, 3, 4, 5]
    assert rep.lint_redaction("nothing sensitive here") == []


def test_render_note_details_collapsed_as_sent() -> None:
    out = rep.render_note_details("2026-08-09-note.md", "note body")
    assert out.startswith("<details>")
    assert "<summary>2026-08-09-note.md (as sent)</summary>" in out
    assert "note body" in out and out.rstrip().endswith("</details>")


def test_attach_note_within_budget_no_overflow() -> None:
    body = "prose\n\n## Environment\n\n```\nx\n```\n"
    payload = rep.attach_note(body, "n.md", "the note text")
    assert payload.overflow_comment is None and payload.truncated is False
    assert "(as sent)" in payload.body and "the note text" in payload.body
    # inserted before the environment block
    assert payload.body.index("the note text") < payload.body.index("## Environment")


def test_attach_note_oversize_excerpts_and_overflows() -> None:
    body = "prose\n\n## Environment\n\n```\nx\n```\n"
    note = "x" * 70_000
    payload = rep.attach_note(body, "n.md", note)
    assert payload.truncated is True
    assert len(payload.body) <= rep.REPORT_BODY_BUDGET
    assert "truncated" in payload.body  # the truncation is flagged in the body
    assert payload.overflow_comment is not None
    assert note in payload.overflow_comment  # the FULL as-sent text
    assert "n.md" in payload.overflow_comment


def test_post_issue_comment_argv_and_failure(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeProc(0)

    monkeypatch.setattr(rep.subprocess, "run", fake_run)
    ok, err = rep.post_issue_comment("o/r", "https://github.com/o/r/issues/9", "full")
    assert ok is True and err == ""
    assert captured["cmd"][:3] == ["gh", "issue", "comment"]
    assert "--repo" in captured["cmd"] and "o/r" in captured["cmd"]

    monkeypatch.setattr(
        rep.subprocess, "run", lambda cmd, **k: _FakeProc(1, "", "boom")
    )
    ok, err = rep.post_issue_comment("o/r", "9", "full")
    assert ok is False and err == "boom"  # error text verbatim


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
