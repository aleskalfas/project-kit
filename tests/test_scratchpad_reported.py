"""Tests for the scratchpad `reported` side-state (COR-043, #643): stamp on
send, manual stamp verb, live read-back listing, drift detection, retirement
from `reported/`, and the report-verb attach/stamp flow (ADR-047 refinement)."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

import project_kit.cli as cli_mod
import project_kit.report as rep
from project_kit import scratchpads
from project_kit.cli import main


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal project tree with `.pkit/scratchpad/{active,done,dropped}/`.
    `reported/` is deliberately absent — it is lazy (COR-043)."""
    scratchpad = tmp_path / ".pkit" / "scratchpad"
    for state in ("active", "done", "dropped"):
        (scratchpad / state).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scratchpads, "_today", lambda: "2026-08-10")
    monkeypatch.setattr(scratchpads, "_today_date", lambda: _dt.date(2026, 8, 10))


@pytest.fixture(autouse=True)
def _pinned_report_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the ADR-050 context resolution to (None, None) so the report-verb
    flow tests never prompt for a name or spawn the pm read-verb subprocess,
    and pin the gh seams (no auth; login 'tester'; kind label always
    ensurable, #663) so the send path never depends on the machine's real gh
    state (#662: gh auth now selects the API-primary path). Tests override
    per-case; the context-stamp test overrides with concrete values."""
    monkeypatch.setattr(
        cli_mod, "_resolve_report_context", lambda *a, **k: (None, None)
    )
    monkeypatch.setattr(rep, "gh_authenticated", lambda: False)
    monkeypatch.setattr(rep, "current_login", lambda: "tester")
    monkeypatch.setattr(rep, "ensure_kind_label", lambda *a, **k: True)


@pytest.fixture(autouse=True)
def fixed_git_author(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_git_config(key: str) -> str:
        return {"user.name": "Test Author", "user.email": "test@example.com"}.get(key, "")

    monkeypatch.setattr(scratchpads, "_git_config", _fake_git_config)


def _stamp_note(kit_target: Path, slug: str = "my-note") -> Path:
    return scratchpads.stamp_new_scratchpad(kit_target, slug=slug)


# --- normalize_issue_ref / helpers -----------------------------------


def test_normalize_issue_ref_passthrough_and_url() -> None:
    assert scratchpads.normalize_issue_ref("owner/repo#12") == "owner/repo#12"
    assert (
        scratchpads.normalize_issue_ref("https://github.com/owner/repo/issues/12")
        == "owner/repo#12"
    )


def test_normalize_issue_ref_rejects_garbage() -> None:
    for bad in ("nonsense", "owner/repo", "owner#12", "https://github.com/owner/repo/pull/3"):
        with pytest.raises(click.ClickException, match=r"invalid issue ref"):
            scratchpads.normalize_issue_ref(bad)


def test_note_slug_strips_date_and_extension() -> None:
    assert scratchpads.note_slug("2026-08-10-my-note.md") == "my-note"


# --- stamp_reported from active/ -------------------------------------


def test_stamp_reported_moves_and_stamps_frontmatter(kit_target: Path) -> None:
    src = _stamp_note(kit_target)
    pre_stamp = src.read_text(encoding="utf-8")
    stamp = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    reported_dir = kit_target / ".pkit" / "scratchpad" / "reported"
    assert not src.exists()
    assert stamp.dst == reported_dir / src.name and stamp.dst.is_file()
    content = stamp.dst.read_text(encoding="utf-8")
    assert "reported: 2026-08-10" in content
    assert "reported_to:\n  - owner/repo#7" in content
    assert f"reported_hash: {scratchpads.content_hash(pre_stamp)}" in content


def test_stamp_reported_hash_is_of_the_file_as_sent(kit_target: Path) -> None:
    src = _stamp_note(kit_target)
    pre_stamp = src.read_text(encoding="utf-8")
    stamp = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    stamped = stamp.dst.read_text(encoding="utf-8")
    # Stripping the reported block recovers the pre-stamp bytes exactly.
    assert scratchpads._strip_reported_frontmatter(stamped) == pre_stamp


def test_stamp_reported_optional_project_workstream(kit_target: Path) -> None:
    _stamp_note(kit_target)
    stamp = scratchpads.stamp_reported(
        kit_target, "my-note", ("owner/repo#7",), project="alpha", workstream="cli"
    )
    content = stamp.dst.read_text(encoding="utf-8")
    assert "project: alpha" in content and "workstream: cli" in content


def test_stamp_reported_omits_absent_context_fields(kit_target: Path) -> None:
    _stamp_note(kit_target)
    stamp = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    content = stamp.dst.read_text(encoding="utf-8")
    assert "project:" not in content and "workstream:" not in content


def test_stamp_reported_dry_run_moves_nothing(kit_target: Path) -> None:
    src = _stamp_note(kit_target)
    stamp = scratchpads.stamp_reported(
        kit_target, "my-note", ("owner/repo#7",), dry_run=True
    )
    assert src.is_file() and not stamp.dst.exists()
    assert not (kit_target / ".pkit" / "scratchpad" / "reported").exists()


def test_stamp_reported_normalizes_url_refs(kit_target: Path) -> None:
    _stamp_note(kit_target)
    stamp = scratchpads.stamp_reported(
        kit_target, "my-note", ("https://github.com/owner/repo/issues/9",)
    )
    assert stamp.added == ("owner/repo#9",)
    assert "  - owner/repo#9" in stamp.dst.read_text(encoding="utf-8")


# --- stamp_reported append (already-reported note) --------------------


def test_stamp_reported_appends_new_refs(kit_target: Path) -> None:
    _stamp_note(kit_target)
    scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    stamp = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#8",))
    assert stamp.src == stamp.dst  # no move on append
    assert stamp.added == ("owner/repo#8",)
    content = stamp.dst.read_text(encoding="utf-8")
    assert scratchpads.read_reported_refs(content) == ("owner/repo#7", "owner/repo#8")


def test_stamp_reported_duplicate_refs_idempotent(kit_target: Path) -> None:
    _stamp_note(kit_target)
    first = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    before = first.dst.read_text(encoding="utf-8")
    again = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    assert again.added == () and again.duplicate == ("owner/repo#7",)
    assert first.dst.read_text(encoding="utf-8") == before  # byte-identical


def test_stamp_reported_append_reanchors_hash(kit_target: Path) -> None:
    _stamp_note(kit_target)
    stamp = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    # Edit after the first send → drift; a new send (append) re-anchors.
    stamp.dst.write_text(
        stamp.dst.read_text(encoding="utf-8") + "\nfollow-up edit\n", encoding="utf-8"
    )
    assert scratchpads.note_is_drifted(stamp.dst.read_text(encoding="utf-8")) is True
    scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#8",))
    assert scratchpads.note_is_drifted(stamp.dst.read_text(encoding="utf-8")) is False


# --- drift detection --------------------------------------------------


def test_note_is_drifted_false_after_stamp_true_after_edit(kit_target: Path) -> None:
    _stamp_note(kit_target)
    stamp = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    assert scratchpads.note_is_drifted(stamp.dst.read_text(encoding="utf-8")) is False
    stamp.dst.write_text(
        stamp.dst.read_text(encoding="utf-8") + "\npost-send edit\n", encoding="utf-8"
    )
    assert scratchpads.note_is_drifted(stamp.dst.read_text(encoding="utf-8")) is True


def test_drifted_reported_notes_lists_names(kit_target: Path) -> None:
    assert scratchpads.drifted_reported_notes(kit_target) == []  # lazy dir absent
    _stamp_note(kit_target)
    stamp = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    assert scratchpads.drifted_reported_notes(kit_target) == []
    stamp.dst.write_text(
        stamp.dst.read_text(encoding="utf-8") + "\nedit\n", encoding="utf-8"
    )
    assert scratchpads.drifted_reported_notes(kit_target) == [stamp.dst.name]


# --- retirement from reported/ + lazy dir removal ---------------------


def test_transition_to_done_from_reported_removes_empty_dir(kit_target: Path) -> None:
    _stamp_note(kit_target)
    scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    src, dst = scratchpads.transition_to_done(
        kit_target, slug="my-note", produced=("owner/repo#7",)
    )
    assert dst.parent == kit_target / ".pkit" / "scratchpad" / "done"
    content = dst.read_text(encoding="utf-8")
    assert "retired: 2026-08-10" in content
    assert "produced:\n  - owner/repo#7" in content
    assert "reported_to:" in content  # the reported archaeology is kept
    assert not src.parent.exists()  # reported/ removed when it empties


def test_transition_to_dropped_from_reported(kit_target: Path) -> None:
    _stamp_note(kit_target)
    scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    _src, dst = scratchpads.transition_to_dropped(kit_target, slug="my-note")
    assert dst.parent == kit_target / ".pkit" / "scratchpad" / "dropped"


def test_reported_dir_kept_while_other_notes_remain(kit_target: Path) -> None:
    _stamp_note(kit_target, "note-one")
    _stamp_note(kit_target, "note-two")
    scratchpads.stamp_reported(kit_target, "note-one", ("owner/repo#7",))
    scratchpads.stamp_reported(kit_target, "note-two", ("owner/repo#8",))
    scratchpads.transition_to_done(kit_target, slug="note-one")
    assert (kit_target / ".pkit" / "scratchpad" / "reported").is_dir()


def test_stamp_new_scratchpad_refuses_slug_in_reported(kit_target: Path) -> None:
    _stamp_note(kit_target)
    scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    with pytest.raises(click.ClickException, match=r"already used"):
        scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")


# --- resolve_note -----------------------------------------------------


def test_resolve_note_by_slug_filename_and_path(kit_target: Path) -> None:
    src = _stamp_note(kit_target)
    assert scratchpads.resolve_note(kit_target, "my-note") == src
    assert scratchpads.resolve_note(kit_target, src.name) == src
    rel = str(src.relative_to(kit_target))
    assert scratchpads.resolve_note(kit_target, rel) == src


def test_resolve_note_finds_reported_notes(kit_target: Path) -> None:
    _stamp_note(kit_target)
    stamp = scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    assert scratchpads.resolve_note(kit_target, "my-note") == stamp.dst


def test_resolve_note_missing_raises(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match=r"no scratchpad note matches"):
        scratchpads.resolve_note(kit_target, "missing")


# --- list_notes (live read-back) --------------------------------------


def test_list_notes_resolves_reported_refs_live(
    kit_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stamp_note(kit_target, "plain-note")
    _stamp_note(kit_target, "sent-note")
    scratchpads.stamp_reported(
        kit_target, "sent-note", ("owner/repo#7", "owner/repo#8")
    )
    resolved = {
        "owner/repo#7": scratchpads.ReportedRefState(
            "owner/repo#7", "closed", title="the fix",
            url="https://github.com/owner/repo/issues/7",
        ),
        "owner/repo#8": scratchpads.ReportedRefState("owner/repo#8", "open"),
    }
    monkeypatch.setattr(scratchpads, "resolve_ref", lambda ref: resolved[ref])
    entries = scratchpads.list_notes(kit_target)
    by_folder = {e.folder: e for e in entries}
    assert by_folder["active"].name == "2026-08-10-plain-note.md"
    reported = by_folder["reported"]
    # title + url ride the same resolve as the state (#678)
    assert reported.refs == (resolved["owner/repo#7"], resolved["owner/repo#8"])
    assert reported.drifted is False


def test_list_notes_offline_degrades_to_unknown(
    kit_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stamp_note(kit_target)
    scratchpads.stamp_reported(kit_target, "my-note", ("owner/repo#7",))
    monkeypatch.setattr(scratchpads, "_gh_json", lambda args: None)  # offline
    entries = scratchpads.list_notes(kit_target)
    # offline: state unknown, no title/url (the render degrades to ref + state)
    assert entries[0].refs[0] == scratchpads.ReportedRefState("owner/repo#7", "unknown")


def test_resolve_ref_reads_state_title_url_in_one_gh_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake(args):
        captured["args"] = args
        return {"state": "CLOSED", "title": "the fix",
                "url": "https://github.com/owner/repo/issues/7"}

    monkeypatch.setattr(scratchpads, "_gh_json", fake)
    assert scratchpads.resolve_ref("owner/repo#7") == scratchpads.ReportedRefState(
        "owner/repo#7", "closed", title="the fix",
        url="https://github.com/owner/repo/issues/7",
    )
    assert captured["args"][:4] == ["gh", "issue", "view", "7"]
    assert "owner/repo" in captured["args"]
    # ONE read carries all three fields (#678) — no extra per-ref round-trip
    assert "state,title,url" in captured["args"]


# --- CLI: scratchpad reported ----------------------------------------


@pytest.fixture
def cli_target(kit_target: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cli_mod, "find_target_root", lambda: kit_target)
    return kit_target


def test_cli_scratchpad_reported_moves_and_records(cli_target: Path) -> None:
    _stamp_note(cli_target)
    res = CliRunner().invoke(
        main, ["scratchpad", "reported", "my-note", "owner/repo#7"]
    )
    assert res.exit_code == 0, res.output
    assert "Moved:" in res.output and "reported/" in res.output
    assert "Recorded: owner/repo#7" in res.output


def test_cli_scratchpad_reported_accepts_issue_url(cli_target: Path) -> None:
    _stamp_note(cli_target)
    res = CliRunner().invoke(
        main,
        ["scratchpad", "reported", "my-note", "https://github.com/owner/repo/issues/9"],
    )
    assert res.exit_code == 0, res.output
    assert "Recorded: owner/repo#9" in res.output


def test_cli_scratchpad_reported_append_and_idempotent(cli_target: Path) -> None:
    _stamp_note(cli_target)
    scratchpads.stamp_reported(cli_target, "my-note", ("owner/repo#7",))
    res = CliRunner().invoke(
        main, ["scratchpad", "reported", "my-note", "owner/repo#8"]
    )
    assert res.exit_code == 0, res.output
    assert "Recorded: owner/repo#8" in res.output and "Moved:" not in res.output
    res = CliRunner().invoke(
        main, ["scratchpad", "reported", "my-note", "owner/repo#8"]
    )
    assert res.exit_code == 0, res.output
    assert "Already recorded: owner/repo#8" in res.output


def test_cli_scratchpad_reported_rejects_bad_ref(cli_target: Path) -> None:
    _stamp_note(cli_target)
    res = CliRunner().invoke(main, ["scratchpad", "reported", "my-note", "nonsense"])
    assert res.exit_code != 0
    assert "invalid issue ref" in res.output


# --- CLI: scratchpad list --------------------------------------------


def test_cli_scratchpad_list_states_drift_and_retire_prompt(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stamp_note(cli_target, "plain-note")
    _stamp_note(cli_target, "sent-note")
    stamp = scratchpads.stamp_reported(cli_target, "sent-note", ("owner/repo#7",))
    stamp.dst.write_text(
        stamp.dst.read_text(encoding="utf-8") + "\nedit\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        scratchpads, "resolve_ref",
        lambda ref: scratchpads.ReportedRefState(
            ref, "closed", title="the fix",
            url="https://github.com/owner/repo/issues/7",
        ),
    )
    res = CliRunner().invoke(main, ["scratchpad", "list"])
    assert res.exit_code == 0, res.output
    assert "active/" in res.output and "2026-08-10-plain-note.md" in res.output
    # a resolved ref renders state + title + url in one row (#678)
    assert (
        "owner/repo#7 (closed) the fix  (https://github.com/owner/repo/issues/7)"
        in res.output
    )
    assert "[modified since reported]" in res.output
    # all refs closed → the retire prompt names the exact done command
    assert (
        "retire with: pkit scratchpad done sent-note --produced owner/repo#7"
        in res.output
    )


def test_cli_scratchpad_list_open_refs_no_retire_prompt(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stamp_note(cli_target)
    scratchpads.stamp_reported(cli_target, "my-note", ("owner/repo#7",))
    monkeypatch.setattr(
        scratchpads, "resolve_ref",
        lambda ref: scratchpads.ReportedRefState(ref, "open"),
    )
    res = CliRunner().invoke(main, ["scratchpad", "list"])
    assert res.exit_code == 0, res.output
    assert "owner/repo#7 (open)" in res.output
    assert "retire with" not in res.output


def test_cli_scratchpad_list_unknown_renders_state_unknown(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stamp_note(cli_target)
    scratchpads.stamp_reported(cli_target, "my-note", ("owner/repo#7",))
    monkeypatch.setattr(scratchpads, "_gh_json", lambda args: None)  # offline
    res = CliRunner().invoke(main, ["scratchpad", "list"])
    assert res.exit_code == 0, res.output
    # the offline degrade is ref + state exactly as before #678 — no
    # empty-title/url artefacts on the row
    assert "owner/repo#7 (state unknown)" in res.output
    assert "http" not in res.output
    assert "retire with" not in res.output  # unknown never counts as closed


def test_cli_scratchpad_done_from_reported(cli_target: Path) -> None:
    _stamp_note(cli_target)
    scratchpads.stamp_reported(cli_target, "my-note", ("owner/repo#7",))
    res = CliRunner().invoke(
        main, ["scratchpad", "done", "my-note", "--produced", "owner/repo#7"]
    )
    assert res.exit_code == 0, res.output
    assert "reported/" in res.output and "done/" in res.output


# --- report --scratchpad: attach + stamp flow -------------------------


def _write_note(kit_target: Path, text: str = "exploration body\n") -> Path:
    note = _stamp_note(kit_target)
    note.write_text(
        note.read_text(encoding="utf-8") + "\n" + text, encoding="utf-8"
    )
    return note


def test_cli_report_attach_inlines_note_and_stamps_on_post(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = _write_note(cli_target, "the exploration text\n")
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda target, **k: "https://github.com/aleskalfas/project-kit/issues/700",
    )
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--file",
         "--scratchpad", "my-note"],
        input="y\n",
    )
    assert res.exit_code == 0, res.output
    assert f"<summary>{note.name} (as sent)</summary>" in res.output
    assert "the exploration text" in res.output
    assert "Stamped reported:" in res.output
    reported = cli_target / ".pkit" / "scratchpad" / "reported" / note.name
    assert reported.is_file() and not note.exists()
    assert "  - aleskalfas/project-kit#700" in reported.read_text(encoding="utf-8")


def test_cli_report_post_stamps_context_into_frontmatter(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The resolved project/workstream pair flows through the #643 stamp
    # kwargs into the reported note's frontmatter (ADR-050).
    note = _write_note(cli_target)
    monkeypatch.setattr(
        cli_mod, "_resolve_report_context", lambda *a, **k: ("alpha", "cli")
    )
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda target, **k: "https://github.com/aleskalfas/project-kit/issues/700",
    )
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--file",
         "--scratchpad", "my-note"],
        input="y\n",
    )
    assert res.exit_code == 0, res.output
    reported = cli_target / ".pkit" / "scratchpad" / "reported" / note.name
    content = reported.read_text(encoding="utf-8")
    assert "project: alpha" in content
    assert "workstream: cli" in content


def test_cli_report_attach_draft_url_path_never_stamps(cli_target: Path) -> None:
    note = _write_note(cli_target)
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--scratchpad", "my-note"],
    )
    assert res.exit_code == 0, res.output
    assert "issues/new?" in res.output
    assert note.is_file()  # URL path sends nothing and stamps nothing
    assert not (cli_target / ".pkit" / "scratchpad" / "reported").exists()


def test_cli_report_attach_yes_stages_and_never_stamps(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # --yes stages for `report submit` (#662) — nothing posts, nothing stamps.
    note = _write_note(cli_target)
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--file", "--yes",
         "--scratchpad", "my-note"],
    )
    assert res.exit_code == 0, res.output
    assert "staged: pkit report submit " in res.output
    assert note.is_file()
    assert not (cli_target / ".pkit" / "scratchpad" / "reported").exists()


def test_cli_report_attach_redaction_prompt_declines(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = _write_note(cli_target, "leaks /Users/alice/secret\n")
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--file",
         "--scratchpad", "my-note"],
        input="n\n",  # decline at the edit-or-send-anyway prompt
    )
    assert res.exit_code == 0, res.output
    assert "un-redacted" in res.output and "Not posted" in res.output
    assert posted["v"] is False
    assert note.is_file()


def test_cli_report_attach_redaction_warns_on_draft_path(cli_target: Path) -> None:
    _write_note(cli_target, "ref $HOME/config\n")
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--scratchpad", "my-note"],
    )
    assert res.exit_code == 0, res.output
    assert "un-redacted" in res.output and "$HOME" in res.output
    assert "issues/new?" in res.output  # the draft still ships, with warnings


def test_cli_report_attach_oversize_single_confirm_posts_both(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_note(cli_target, "y" * 70_000 + "\n")
    comment_calls: list = []
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda target, **k: "https://github.com/aleskalfas/project-kit/issues/701",
    )
    monkeypatch.setattr(
        rep, "post_issue_comment",
        lambda target, issue, body: comment_calls.append((issue, body)) or (True, ""),
    )
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--file",
         "--scratchpad", "my-note"],
        input="y\n",  # ONE confirm covers body + overflow comment
    )
    assert res.exit_code == 0, res.output
    assert "ONE overflow comment" in res.output
    assert len(comment_calls) == 1
    assert "y" * 70_000 in comment_calls[0][1]  # the FULL note text
    assert "Stamped reported:" in res.output


def test_cli_report_attach_partial_failure_does_not_stamp(
    cli_target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = _write_note(cli_target, "y" * 70_000 + "\n")
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda target, **k: "https://github.com/aleskalfas/project-kit/issues/702",
    )
    monkeypatch.setattr(
        rep, "post_issue_comment", lambda target, issue, body: (False, "boom")
    )
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--file",
         "--scratchpad", "my-note"],
        input="y\n",
    )
    assert res.exit_code == 0, res.output
    # ADR-047 refinement: the send did not complete as confirmed —
    # nothing stamped, issue named, error verbatim, remediation printed.
    assert "issues/702" in res.output
    assert "boom" in res.output
    assert "NOT stamped" in res.output and "Remediation" in res.output
    assert note.is_file()
    assert not (cli_target / ".pkit" / "scratchpad" / "reported").exists()


def test_cli_report_attach_missing_note_errors(cli_target: Path) -> None:
    res = CliRunner().invoke(
        main,
        ["report", "bug", "--title", "t", "--body", "b", "--scratchpad", "missing"],
    )
    assert res.exit_code != 0
    assert "no scratchpad note matches" in res.output


# --- pre-send drift lint ---------------------------------------------


def test_cli_report_warns_on_drifted_reported_note(cli_target: Path) -> None:
    _stamp_note(cli_target)
    stamp = scratchpads.stamp_reported(cli_target, "my-note", ("owner/repo#7",))
    stamp.dst.write_text(
        stamp.dst.read_text(encoding="utf-8") + "\nedit\n", encoding="utf-8"
    )
    res = CliRunner().invoke(main, ["report", "bug", "--title", "t", "--body", "b"])
    assert res.exit_code == 0, res.output
    assert "modified since reported" in res.output
    assert stamp.dst.name in res.output
    assert "issues/new?" in res.output  # a warning, never a gate


def test_cli_report_no_warning_without_drift(cli_target: Path) -> None:
    _stamp_note(cli_target)
    scratchpads.stamp_reported(cli_target, "my-note", ("owner/repo#7",))
    res = CliRunner().invoke(main, ["report", "bug", "--title", "t", "--body", "b"])
    assert res.exit_code == 0, res.output
    assert "modified since reported" not in res.output
