"""Tests for the `pkit report` composition logic (PRJ-008 / ADR-047)."""

from __future__ import annotations

import urllib.parse
from pathlib import Path

import pytest

import project_kit.cli as cli_mod
import project_kit.report as _rep_for_pins
from project_kit.report import (
    KINDS,
    REPORT_TARGET,
    build_new_issue_url,
    compose_report,
    compose_report_body,
)

#: The real context resolver, captured before the autouse pin below replaces
#: it — the ADR-050 prompt-flow tests restore it explicitly.
_REAL_RESOLVE_CONTEXT = cli_mod._resolve_report_context

#: Real gh seams, captured before the autouse pins below replace them —
#: tests exercising the real functions restore these explicitly.
_REAL_GH_AUTHENTICATED = _rep_for_pins.gh_authenticated
_REAL_CURRENT_LOGIN = _rep_for_pins.current_login
_REAL_ENSURE_KIND_LABEL = _rep_for_pins.ensure_kind_label


@pytest.fixture(autouse=True)
def _pinned_report_context(monkeypatch):
    """Pin the ADR-050 context resolution to (None, None) so CLI tests never
    prompt for a name or spawn the pm read-verb subprocess, and pin the gh
    seams (no auth; login 'tester'; kind label always ensurable) so no test's
    send path depends on the machine's real gh state (#662: gh auth now
    selects the API-primary path; #663: the post ensures the kind label).
    Tests override per-case (or restore the captured real functions)."""
    monkeypatch.setattr(
        cli_mod, "_resolve_report_context", lambda *a, **k: (None, None)
    )
    monkeypatch.setattr(_rep_for_pins, "gh_authenticated", lambda: False)
    monkeypatch.setattr(_rep_for_pins, "current_login", lambda: "tester")
    monkeypatch.setattr(_rep_for_pins, "ensure_kind_label", lambda *a, **k: True)


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
    assert title == "[Bug] T"  # every kind carries a prefix (#663)
    assert "## Environment" in body
    assert "P" in body
    assert REPORT_TARGET in url
    assert "issues/new?" in url


def test_compose_report_feedback_kind_labels_feedback(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    _, _, url = compose_report("feedback", title="T", prose="P", target_root=tmp_path)
    q = urllib.parse.parse_qs(url.split("?", 1)[1])
    assert q["labels"] == ["report:feedback"]  # namespaced (#663)


def test_compose_report_prefixes_every_kind(tmp_path: Path) -> None:
    # #663: all three kinds carry a title prefix + the namespaced label in
    # the URL prefill (harmless where GitHub drops it — prefix+marker carry
    # the kind there).
    (tmp_path / ".pkit").mkdir()
    for kind, prefix in rep.KIND_TITLE_PREFIXES.items():
        title, _, url = compose_report(
            kind, title="T", prose="P", target_root=tmp_path
        )
        assert title == f"{prefix} T"
        q = urllib.parse.parse_qs(url.split("?", 1)[1])
        assert q["title"] == [f"{prefix} T"]
        assert q["labels"] == [rep.KIND_LABELS[kind]]


def test_compose_report_does_not_double_any_prefix(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    for kind, prefix in rep.KIND_TITLE_PREFIXES.items():
        title, _, _ = compose_report(
            kind, title=f"{prefix} already", prose="P", target_root=tmp_path
        )
        assert title == f"{prefix} already"


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
    assert q["labels"] == ["report:change-request"]
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
    # precedence: label (namespaced, then legacy) > marker > prefix (#663)
    assert rep.classify_kind(["report:bug"], "[CR] t", "") == "bug"
    assert rep.classify_kind(["bug"], "[CR] t", "") == "bug"  # legacy name still read
    assert rep.classify_kind(
        ["report:feedback", "bug"], "t", ""
    ) == "feedback"  # namespaced beats legacy
    assert rep.classify_kind([], "t", "<!-- pkit-report: kind=feedback -->") == "feedback"
    assert rep.classify_kind(
        [], "[Bug] t", "<!-- pkit-report: kind=feedback -->"
    ) == "feedback"  # marker beats prefix
    assert rep.classify_kind([], "[CR] add a flag", "") == "change-request"
    assert rep.classify_kind([], "[Bug] it crashes", "") == "bug"
    assert rep.classify_kind([], "[Feedback] some thoughts", "") == "feedback"
    assert rep.classify_kind([], "unrelated CR mention", "prose") == ""


def test_classify_kind_660_shape_prefix_only_feedback() -> None:
    # The exact shape that rendered as bare 'report' pre-#663: a
    # [Feedback]-prefixed title, no report label, no body marker (#660 was
    # URL-filed, so GitHub dropped its label).
    title = (
        "[Feedback] pkit report channel — friction inventory "
        "(keep the consent gate, secure the gated path)"
    )
    assert rep.classify_kind(["enhancement"], title, "## The through-line") == "feedback"


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
    assert "labels=report%3Abug" in res.output  # namespaced label prefill (#663)
    assert "environment block" in res.output.lower()


def test_cli_report_feedback_labels_feedback() -> None:
    res = CliRunner().invoke(
        main, ["report", "feedback", "--title", "t", "--body", "some thoughts"]
    )
    assert res.exit_code == 0, res.output
    assert "labels=report%3Afeedback" in res.output


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
    url = rep.file_report_via_gh("owner/repo", title="T", body="B", label="report:bug")
    assert url == "https://github.com/owner/repo/issues/99"
    assert captured["cmd"][:5] == ["gh", "issue", "create", "--repo", "owner/repo"]
    assert "--label" in captured["cmd"] and "report:bug" in captured["cmd"]


def test_file_report_via_gh_no_label_omits_flag(monkeypatch) -> None:
    # label=None is the ensure-failure degrade (#663): post unlabelled rather
    # than block the send.
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeProc(0, "url\n")

    monkeypatch.setattr(rep.subprocess, "run", fake_run)
    assert rep.file_report_via_gh("o/r", title="T", body="B", label=None) == "url"
    assert "--label" not in captured["cmd"]


def test_file_report_via_gh_failure_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(rep.subprocess, "run", lambda cmd, **k: _FakeProc(1, "", "boom"))
    assert rep.file_report_via_gh("o/r", title="T", body="B", label="report:bug") is None


# --- kind labels: ensure-then-apply (#663) ----------------------------


def test_ensure_kind_label_present_skips_create(monkeypatch) -> None:
    monkeypatch.setattr(rep, "ensure_kind_label", _REAL_ENSURE_KIND_LABEL)
    monkeypatch.setattr(rep, "_gh_json", lambda args: [{"name": "report:bug"}])
    monkeypatch.setattr(
        rep.subprocess, "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("create must not run")),
    )
    assert rep.ensure_kind_label("o/r", "bug") is True


def test_ensure_kind_label_creates_when_missing_once(monkeypatch) -> None:
    monkeypatch.setattr(rep, "ensure_kind_label", _REAL_ENSURE_KIND_LABEL)
    monkeypatch.setattr(rep, "_gh_json", lambda args: [])  # label absent
    creates: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        creates.append(cmd)
        return _FakeProc(0)

    monkeypatch.setattr(rep.subprocess, "run", fake_run)
    assert rep.ensure_kind_label("o/r", "feedback") is True
    assert len(creates) == 1  # create-if-missing fires exactly once
    cmd = creates[0]
    assert cmd[:4] == ["gh", "label", "create", "report:feedback"]
    assert "--repo" in cmd and "o/r" in cmd
    assert "--color" in cmd
    assert rep.KIND_LABEL_DESCRIPTION in cmd  # "pkit report kind"


def test_ensure_kind_label_tolerates_already_exists(monkeypatch) -> None:
    # A failed list read falls through to create; an "already exists" refusal
    # is the desired end state, not a failure.
    monkeypatch.setattr(rep, "ensure_kind_label", _REAL_ENSURE_KIND_LABEL)
    monkeypatch.setattr(rep, "_gh_json", lambda args: None)
    monkeypatch.setattr(
        rep.subprocess, "run",
        lambda *a, **k: _FakeProc(1, "", "label already exists on o/r"),
    )
    assert rep.ensure_kind_label("o/r", "bug") is True


def test_ensure_kind_label_create_failure_returns_false(monkeypatch) -> None:
    monkeypatch.setattr(rep, "ensure_kind_label", _REAL_ENSURE_KIND_LABEL)
    monkeypatch.setattr(rep, "_gh_json", lambda args: [])
    monkeypatch.setattr(
        rep.subprocess, "run", lambda *a, **k: _FakeProc(1, "", "HTTP 403")
    )
    assert rep.ensure_kind_label("o/r", "bug") is False


def test_gh_authenticated_false_when_gh_absent(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", _REAL_GH_AUTHENTICATED)
    monkeypatch.setattr(rep.shutil, "which", lambda _name: None)
    assert rep.gh_authenticated() is False


def test_cli_file_yes_stages_and_does_not_post(tmp_path, monkeypatch) -> None:
    # --file --yes must NEVER auto-post the foreign write (ADR-047) — since
    # #662 it stages the payload for `pkit report submit` instead.
    posted = {"v": False}
    (tmp_path / ".pkit").mkdir()
    monkeypatch.setattr(cli_mod, "find_target_root", lambda: tmp_path)
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--file", "--yes"]
    )
    assert res.exit_code == 0, res.output
    assert posted["v"] is False
    assert "staged: pkit report submit " in res.output
    assert rep.list_staged(tmp_path)  # the payload landed as a draft


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
    monkeypatch.setattr(rep, "current_login", _REAL_CURRENT_LOGIN)

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
    monkeypatch.setattr(rep, "current_login", _REAL_CURRENT_LOGIN)

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
    assert "labels=report%3Achange-request" in res.output
    assert urllib.parse.quote_plus("[CR] add a flag") in res.output


def test_cli_change_request_file_yes_stages_and_does_not_post(
    tmp_path, monkeypatch
) -> None:
    # same ADR-047 asymmetry as bug/feedback: --file --yes NEVER auto-posts —
    # it stages for `report submit` (#662).
    posted = {"v": False}
    (tmp_path / ".pkit").mkdir()
    monkeypatch.setattr(cli_mod, "find_target_root", lambda: tmp_path)
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main,
        ["report", "change-request", "--title", "t", "--body", "b", "--file", "--yes"],
    )
    assert res.exit_code == 0, res.output
    assert posted["v"] is False
    assert "staged: pkit report submit " in res.output
    drafts = rep.list_staged(tmp_path)
    assert [d.kind for d in drafts] == ["change-request"]


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


def test_list_inbox_queries_labels_and_prefix_search_per_kind(monkeypatch) -> None:
    seen: list[list[str]] = []

    def fake(args):
        seen.append(args)
        return []

    monkeypatch.setattr(rep, "_gh_json", fake)
    for kind in rep.KINDS:
        seen.clear()
        rep.list_inbox("o/r", kind=kind)
        assert any("--label" in q and rep.KIND_LABELS[kind] in q for q in seen)
        assert any("--label" in q and kind in q for q in seen)  # legacy labels
        # discovers label-less URL-filed reports by their title prefix (#663)
        prefix_query = f'"{rep.KIND_TITLE_PREFIXES[kind]}" in:title'
        assert any("--search" in q and prefix_query in q for q in seen)


def test_list_inbox_discovers_prefix_only_feedback(monkeypatch) -> None:
    # the #660 shape end-to-end through the inbox: [Feedback]-titled, no
    # report label (only the repo's own vocabulary), no marker.
    issues = [{
        "number": 660, "title": "[Feedback] friction inventory", "state": "OPEN",
        "labels": [{"name": "enhancement"}], "updatedAt": "2026-08-10",
        "body": "no marker here",
    }]
    monkeypatch.setattr(rep, "_gh_json", lambda args: issues)
    inbox = rep.list_inbox("o/r", kind="feedback")
    assert [r.number for r in inbox] == [660]
    assert inbox[0].kind == "feedback"


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


# --- project + workstream context (ADR-050 / #644) -------------------

from project_kit import report_context as rc_mod  # noqa: E402


def test_compose_report_renders_context_line_marker_and_title(
    tmp_path: Path,
) -> None:
    (tmp_path / ".pkit").mkdir()
    title, body, _ = compose_report(
        "bug", title="T", prose="P", target_root=tmp_path,
        project="alpha", workstream="cli",
    )
    assert title == "[Bug] T (alpha)"  # kind prefix, then title, then parenthetical
    # the context line is the FIRST body line, right under the issue title
    assert body.splitlines()[0] == "Project: alpha · Workstream: cli"
    assert rep.parse_report_marker(body) == {
        "kind": "bug", "project": "alpha", "workstream": "cli",
    }


def test_compose_change_request_title_parenthetical_after_prefix(
    tmp_path: Path,
) -> None:
    (tmp_path / ".pkit").mkdir()
    title, _, _ = compose_report(
        "change-request", title="add a flag", prose="x", target_root=tmp_path,
        project="alpha",
    )
    assert title == "[CR] add a flag (alpha)"


def test_compose_report_unresolved_project_states_omission(
    tmp_path: Path,
) -> None:
    (tmp_path / ".pkit").mkdir()
    title, body, _ = compose_report(
        "bug", title="T", prose="P", target_root=tmp_path,
    )
    assert title == "[Bug] T"  # no parenthetical without a name
    assert "(project: not declared)" in body  # explicit, never silent
    assert "Project:" not in body
    marker = rep.parse_report_marker(body)
    assert "project" not in marker and "workstream" not in marker


def test_cli_workstream_flag_overrides_pm_derivation(monkeypatch) -> None:
    monkeypatch.setattr(cli_mod, "_resolve_report_context", _REAL_RESOLVE_CONTEXT)
    monkeypatch.setattr(rc_mod, "read_project_name", lambda root: "alpha")

    def explode(root):  # pragma: no cover - must not be reached
        raise AssertionError("--workstream must skip the pm subprocess")

    monkeypatch.setattr(rc_mod, "pm_workstream", explode)
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--workstream", "cli-x"],
    )
    assert res.exit_code == 0, res.output
    assert urllib.parse.quote_plus("Workstream: cli-x") in res.output


def test_cli_workstream_derived_via_pm_verb(monkeypatch) -> None:
    monkeypatch.setattr(cli_mod, "_resolve_report_context", _REAL_RESOLVE_CONTEXT)
    monkeypatch.setattr(rc_mod, "read_project_name", lambda root: "alpha")
    monkeypatch.setattr(rc_mod, "pm_workstream", lambda root: "derived-ws")
    res = CliRunner().invoke(main, ["report", "bug", "--title", "t", "--body", "b"])
    assert res.exit_code == 0, res.output
    assert urllib.parse.quote_plus("Project: alpha · Workstream: derived-ws") in res.output


def test_cli_draft_path_uses_remote_fallback_without_prompt(
    tmp_path: Path, monkeypatch
) -> None:
    # Non-interactive/draft compose: config -> remote fallback, silently.
    (tmp_path / ".pkit").mkdir()
    monkeypatch.setattr(cli_mod, "find_target_root", lambda: tmp_path)
    monkeypatch.setattr(cli_mod, "_resolve_report_context", _REAL_RESOLVE_CONTEXT)
    monkeypatch.setattr(rc_mod, "git_remote_repo_name", lambda root: "remote-repo")
    monkeypatch.setattr(rc_mod, "pm_workstream", lambda root: None)
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b"]
    )  # no input at all: a prompt would abort on EOF
    assert res.exit_code == 0, res.output
    assert urllib.parse.quote_plus("Project: remote-repo") in res.output


def test_cli_interactive_compose_prompts_once_and_writes_back(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / ".pkit").mkdir()
    monkeypatch.setattr(cli_mod, "find_target_root", lambda: tmp_path)
    monkeypatch.setattr(cli_mod, "_resolve_report_context", _REAL_RESOLVE_CONTEXT)
    monkeypatch.setattr(rc_mod, "git_remote_repo_name", lambda root: None)
    monkeypatch.setattr(rc_mod, "pm_workstream", lambda root: None)
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda target, **k: "https://github.com/aleskalfas/project-kit/issues/700",
    )
    # name prompt -> save-confirm (default yes) -> post-confirm
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--file"],
        input="myproj\ny\ny\n",
    )
    assert res.exit_code == 0, res.output
    assert "Save name 'myproj'" in res.output
    assert rc_mod.read_project_name(tmp_path) == "myproj"  # written back

    # Second compose: the declared name resolves — no prompt fires (the only
    # input consumed is the post-confirm).
    res2 = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--file"],
        input="y\n",
    )
    assert res2.exit_code == 0, res2.output
    assert "Save name" not in res2.output
    assert "Project: myproj" in res2.output  # echoed body carries the context


def test_cli_interactive_prompt_blank_omits_and_writes_nothing(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / ".pkit").mkdir()
    monkeypatch.setattr(cli_mod, "find_target_root", lambda: tmp_path)
    monkeypatch.setattr(cli_mod, "_resolve_report_context", _REAL_RESOLVE_CONTEXT)
    monkeypatch.setattr(rc_mod, "git_remote_repo_name", lambda root: None)
    monkeypatch.setattr(rc_mod, "pm_workstream", lambda root: None)
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(rep, "file_report_via_gh", lambda target, **k: "url")
    # blank name -> no save-confirm -> decline the post
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--file"],
        input="\nn\n",
    )
    assert res.exit_code == 0, res.output
    assert "(project: not declared)" in res.output
    assert not rc_mod.project_config_path(tmp_path).exists()


def test_list_my_reports_fetches_bodies_and_reads_project_marker(
    monkeypatch,
) -> None:
    monkeypatch.setattr(rep, "current_login", _REAL_CURRENT_LOGIN)
    queries: list[list[str]] = []

    def fake(args):
        queries.append(args)
        if args[:3] == ["gh", "api", "user"]:
            return None  # no login -> attributed query skipped
        return [{
            "number": 1, "title": "a bug", "state": "OPEN",
            "labels": [{"name": "bug"}], "updatedAt": "2026-08-01",
            "body": "p\n<!-- pkit-report: kind=bug project=alpha workstream=cli -->\n",
        }]

    monkeypatch.setattr(rep, "_gh_json", fake)
    reports = rep.list_my_reports("o/r")
    assert reports[0].project == "alpha" and reports[0].workstream == "cli"
    list_query = next(q for q in queries if "list" in q)
    assert "body" in list_query[list_query.index("--json") + 1]


def test_cli_report_list_shows_project_per_row(monkeypatch) -> None:
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "list_my_reports",
        lambda t: [rep.ReportSummary(
            1, "a bug", "bug", "open", "2026-08-01", project="alpha"
        )],
    )
    res = CliRunner().invoke(main, ["report"])
    assert res.exit_code == 0
    assert "[alpha]" in res.output


def test_cli_inbox_group_by_project_end_to_end_from_markers(monkeypatch) -> None:
    # markers -> _gh_json -> list_inbox -> grouped CLI output, no seam mocked
    # between the marker parse and the rendering.
    issues = [
        {"number": 1, "title": "a bug", "state": "OPEN",
         "labels": [{"name": "bug"}], "updatedAt": "2026-08-01",
         "body": "p\n<!-- pkit-report: kind=bug project=alpha workstream=cli -->\n"},
        {"number": 2, "title": "fb", "state": "OPEN",
         "labels": [{"name": "feedback"}], "updatedAt": "2026-08-02",
         "body": "p\n<!-- pkit-report: kind=feedback project=beta -->\n"},
        {"number": 3, "title": "bare", "state": "OPEN",
         "labels": [{"name": "feedback"}], "updatedAt": "2026-08-03",
         "body": "no marker"},
    ]
    monkeypatch.setattr(rep, "in_report_target", lambda: True)
    monkeypatch.setattr(rep, "_gh_json", lambda args: issues)
    res = CliRunner().invoke(main, ["report", "inbox", "--group-by", "project"])
    assert res.exit_code == 0, res.output
    lines = res.output.splitlines()
    assert any(ln.strip() == "alpha" for ln in lines)
    assert any(ln.strip() == "beta" for ln in lines)
    assert any(ln.strip() == "(no project)" for ln in lines)
    assert "[cli]" in res.output  # workstream shown on #1's row
    # each report renders under its own project group
    assert lines.index(next(ln for ln in lines if ln.strip() == "alpha")) < \
        lines.index(next(ln for ln in lines if "#1" in ln))


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


def test_cli_report_show_unclassifiable_issue_says_so(monkeypatch) -> None:
    # An issue the classifier can't place renders as 'unclassified', not as
    # the kind-masquerading 'report' that #660 surfaced pre-#663.
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "show_report",
        lambda t, n: {
            "number": 5, "title": "not a report", "state": "open", "kind": "",
            "comments": [], "tracked_by": {},
        },
    )
    res = CliRunner().invoke(main, ["report", "show", "5"])
    assert res.exit_code == 0
    assert "unclassified" in res.output
