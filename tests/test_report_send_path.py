"""Tests for the report channel's send path (#662, ADR-047 realization).

API-primary confirm flow with the posting identity named, the URL survivor
path (budget + browser-identity warning + `--open`), and the `--yes` stage +
interactive-only `report submit` split. gh and the browser are monkeypatched
throughout — nothing here touches the network.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

import project_kit.cli as cli_mod
import project_kit.report as rep
from project_kit.cli import main
from project_kit.report import REPORT_TARGET, SendPayload


@pytest.fixture(autouse=True)
def _pinned_seams(monkeypatch):
    """Same pins as test_report.py: context resolution silent, gh seams
    deterministic (no auth by default; login 'tester'; kind label always
    ensurable, #663). Tests override."""
    monkeypatch.setattr(
        cli_mod, "_resolve_report_context", lambda *a, **k: (None, None)
    )
    monkeypatch.setattr(rep, "gh_authenticated", lambda: False)
    monkeypatch.setattr(rep, "current_login", lambda: "tester")
    monkeypatch.setattr(rep, "ensure_kind_label", lambda *a, **k: True)


@pytest.fixture
def target(tmp_path: Path, monkeypatch) -> Path:
    """A minimal target root, wired as the CLI's resolved project."""
    (tmp_path / ".pkit").mkdir()
    monkeypatch.setattr(cli_mod, "find_target_root", lambda: tmp_path)
    return tmp_path


_NOTE_FRONTMATTER = "---\nauthors:\n  - Test <t@example.com>\nstarted: 2026-08-11\n---\n\n"


def _note(target: Path, text: str, name: str = "2026-08-11-send-note.md") -> Path:
    """An active scratchpad note with the frontmatter the reported-stamp
    machinery expects."""
    active = target / ".pkit" / "scratchpad" / "active"
    active.mkdir(parents=True, exist_ok=True)
    path = active / name
    path.write_text(_NOTE_FRONTMATTER + text, encoding="utf-8")
    return path


# --- API-primary gated path ------------------------------------------


def test_api_post_is_default_and_names_identity_and_target(
    target: Path, monkeypatch
) -> None:
    # gh authenticated, no flags: the confirm-gated API post is the path.
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda t, **k: f"https://github.com/{t}/issues/700",
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b"], input="y\n"
    )
    assert res.exit_code == 0, res.output
    assert "issues/new?" not in res.output  # never URL-embedded on this path
    assert f"PUBLIC bug issue to {REPORT_TARGET} as @tester" in res.output
    assert f"Post as @tester to {REPORT_TARGET}?" in res.output
    assert "filed:" in res.output and "700" in res.output


def test_api_post_decline_does_not_post(target: Path, monkeypatch) -> None:
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b"], input="n\n"
    )
    assert res.exit_code == 0, res.output
    assert posted["v"] is False
    assert "Not posted" in res.output


def test_api_post_scratchpad_note_posts_body_and_stamps(
    target: Path, monkeypatch
) -> None:
    # A real note travels as the issue body via gh — no URL involved — and is
    # stamped reported on the fully-successful post (COR-043).
    note = _note(target, "# Note\n\na perfectly clean note\n")
    sent = {}

    def fake_post(t, *, title, body, label):
        sent["body"] = body
        return f"https://github.com/{t}/issues/701"

    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(rep, "file_report_via_gh", fake_post)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name],
        input="y\n",
    )
    assert res.exit_code == 0, res.output
    assert "a perfectly clean note" in sent["body"]
    assert "Stamped reported" in res.output
    assert (target / ".pkit" / "scratchpad" / "reported" / note.name).exists()


# --- kind visibility on the API post (#663) ---------------------------


def test_api_post_ensures_then_applies_namespaced_label(
    target: Path, monkeypatch
) -> None:
    ensured: list[tuple[str, str]] = []
    sent: dict = {}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "ensure_kind_label", lambda t, k: ensured.append((t, k)) or True
    )

    def fake_post(t, *, title, body, label):
        sent["title"], sent["label"] = title, label
        return f"https://github.com/{t}/issues/705"

    monkeypatch.setattr(rep, "file_report_via_gh", fake_post)
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b"], input="y\n"
    )
    assert res.exit_code == 0, res.output
    assert ensured == [(REPORT_TARGET, "bug")]  # ensure ran, exactly once
    assert sent["label"] == "report:bug"  # then the namespaced label applied
    assert sent["title"].startswith("[Bug] ")  # prefix survives to the post
    assert "filed:" in res.output


def test_api_post_label_failure_degrades_with_warning_and_posts(
    target: Path, monkeypatch
) -> None:
    sent: dict = {}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(rep, "ensure_kind_label", lambda t, k: False)

    def fake_post(t, *, title, body, label):
        sent["label"] = label
        return f"https://github.com/{t}/issues/706"

    monkeypatch.setattr(rep, "file_report_via_gh", fake_post)
    res = CliRunner().invoke(
        main, ["report", "feedback", "--title", "t", "--body", "b"], input="y\n"
    )
    assert res.exit_code == 0, res.output
    assert sent["label"] is None  # posted WITHOUT the label — never blocked
    assert "[warn]" in res.output and "report:feedback" in res.output
    assert "filed:" in res.output and "706" in res.output


# --- URL survivor path -----------------------------------------------


def test_no_auth_url_path_warns_about_browser_identity(target: Path) -> None:
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b"]
    )
    assert res.exit_code == 0, res.output
    assert "issues/new?" in res.output
    assert "WHOEVER YOUR BROWSER IS LOGGED IN AS" in res.output


def test_explicit_url_flag_overrides_api_default(target: Path, monkeypatch) -> None:
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--url"]
    )
    assert res.exit_code == 0, res.output
    assert posted["v"] is False
    assert "issues/new?" in res.output
    assert "WHOEVER YOUR BROWSER IS LOGGED IN AS" in res.output


def test_oversized_url_is_refused_with_api_alternative(
    target: Path, monkeypatch
) -> None:
    # A scratchpad-backed prefill blows the URL budget: the URL form must
    # refuse (it would hard-fail on open, #662), naming the working path.
    note = _note(target, "x" * (rep.URL_BUDGET * 2))
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name, "--url"],
    )
    assert res.exit_code != 0
    assert "over the" in res.output and str(rep.URL_BUDGET) in res.output
    assert "issues/new?" not in res.output  # no unusable URL is printed
    assert "API path" in res.output


def test_oversized_url_without_auth_points_to_stage_and_submit(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "x" * (rep.URL_BUDGET * 2))
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name],
    )
    assert res.exit_code != 0
    assert "gh auth login" in res.output
    assert "pkit report submit" in res.output


def test_open_flag_opens_within_budget_url(target: Path, monkeypatch) -> None:
    opened = {}
    monkeypatch.setattr(
        rep, "open_in_browser", lambda url: opened.__setitem__("url", url) or True
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--open"]
    )
    assert res.exit_code == 0, res.output
    assert opened["url"].startswith("https://github.com/")
    assert "Opened in your browser" in res.output


def test_open_flag_degrades_to_printed_url(target: Path, monkeypatch) -> None:
    monkeypatch.setattr(rep, "open_in_browser", lambda url: False)
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--open"]
    )
    assert res.exit_code == 0, res.output
    assert "issues/new?" in res.output  # printed before the open attempt
    assert "Could not open a browser" in res.output


# --- --yes stages, never posts (the ADR-047 asymmetry, pinned) --------


def test_yes_stages_prints_submit_root_and_store_and_never_posts(
    target: Path, monkeypatch
) -> None:
    # The stage message is deliberately TIGHT (it exists to keep agent output
    # noise-free) but must name where the draft landed: the resolved project
    # root and the per-project draft store (#693).
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--yes"]
    )
    assert res.exit_code == 0, res.output
    assert posted["v"] is False  # the asymmetry: --yes NEVER posts
    lines = [ln for ln in res.output.splitlines() if ln.strip()]
    assert len(lines) <= 3  # short — the agent hand-off, not a wall
    assert lines[0].startswith("staged: pkit report submit ")  # command first
    assert f"project root: {target}" in lines[1]
    assert str(rep.drafts_dir(target)) in lines[2]


def test_yes_stage_title_carries_kind_prefix(target: Path) -> None:
    # the prefix is stamped at compose, so a staged draft already carries it
    # (#663) — submit posts the staged title verbatim.
    res = CliRunner().invoke(
        main, ["report", "feedback", "--title", "t", "--body", "b", "--yes"]
    )
    assert res.exit_code == 0, res.output
    (draft,) = rep.list_staged(target)
    assert draft.title == "[Feedback] t"


def test_yes_stage_file_lands_gitignored(target: Path) -> None:
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--yes"]
    )
    assert res.exit_code == 0, res.output
    drafts_dir = target / rep.DRAFTS_RELPATH
    assert (drafts_dir / ".gitignore").read_text(encoding="utf-8") == "*\n"
    drafts = rep.list_staged(target)
    assert len(drafts) == 1
    assert drafts[0].kind == "bug" and drafts[0].target == REPORT_TARGET


def test_yes_stage_carries_redaction_findings_as_header_warnings(
    target: Path,
) -> None:
    note = _note(target, "path /Users/alice/project leaked\n")
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name, "--yes"],
    )
    assert res.exit_code == 0, res.output
    (draft,) = rep.list_staged(target)
    assert any("macOS home path" in w for w in draft.warnings)
    header = draft.path.read_text(encoding="utf-8").split("---\n")[1]
    assert "warning: line 7: macOS home path" in header  # findings ride the header


def test_yes_stage_roundtrips_oversize_overflow_comment(target: Path) -> None:
    note = _note(target, "y" * 70_000)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name, "--yes"],
    )
    assert res.exit_code == 0, res.output
    (draft,) = rep.list_staged(target)
    assert draft.payload.truncated is True
    assert draft.payload.overflow_comment is not None
    assert "y" * 70_000 in draft.payload.overflow_comment
    assert len(draft.payload.body) <= rep.REPORT_BODY_BUDGET


# --- composing outside a project (#693) -------------------------------


@pytest.fixture
def no_project(tmp_path: Path, monkeypatch) -> Path:
    """A scratch directory that is NOT a pkit project: `find_target_root`
    resolves nothing, exactly as in a temp dir a report body was drafted in."""
    monkeypatch.setattr(cli_mod, "find_target_root", lambda: None)
    monkeypatch.chdir(tmp_path)
    return Path.cwd()  # resolved form — what the CLI will print


def test_no_project_compose_warns_loudly(no_project: Path) -> None:
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--yes"]
    )
    assert res.exit_code == 0, res.output  # composes anyway — never refuses
    assert f"no pkit project found at {no_project}" in res.output
    assert "project root" in res.output  # names how to fix it


def test_no_project_compose_marks_env_unresolved_not_empty(
    no_project: Path,
) -> None:
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--yes"]
    )
    assert res.exit_code == 0, res.output
    (draft,) = rep.list_staged(no_project)
    body = draft.payload.body
    assert "## Environment" in body  # the fenced block keeps its shape
    assert "NOT COLLECTED" in body
    # …and NONE of the values a maintainer would read as facts about the install
    assert "(none installed)" not in body
    assert "backbone:" not in body and "adapter:" not in body


def test_no_project_compose_body_carries_no_filesystem_path(
    no_project: Path,
) -> None:
    # The warning names the directory (terminal); the ISSUE body never may.
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--yes"]
    )
    assert res.exit_code == 0, res.output
    (draft,) = rep.list_staged(no_project)
    body = draft.payload.body
    assert str(no_project) not in body
    assert rep.lint_redaction(body) == []


def test_no_project_stage_message_says_no_project(no_project: Path) -> None:
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--yes"]
    )
    assert res.exit_code == 0, res.output
    lines = [ln for ln in res.output.splitlines() if ln.strip()]
    assert f"project root: no project — {no_project}" in lines[-2]
    assert str(rep.drafts_dir(no_project)) in lines[-1]


def test_in_project_compose_is_unchanged(target: Path) -> None:
    # The in-project path keeps collecting and rendering the real block.
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--yes"]
    )
    assert res.exit_code == 0, res.output
    assert "no pkit project found" not in res.output
    (draft,) = rep.list_staged(target)
    body = draft.payload.body
    assert "backbone:" in body and "adapter:" in body
    assert "NOT COLLECTED" not in body


# --- report submit ----------------------------------------------------


def _stage_via_cli(target: Path, *extra: str) -> str:
    """Stage a bug draft through the CLI; returns the draft id."""
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--yes", *extra]
    )
    assert res.exit_code == 0, res.output
    staged = next(
        ln for ln in res.output.splitlines() if ln.startswith("staged: ")
    )
    return staged.rsplit(" ", 1)[-1]


def test_submit_bare_lists_staged_drafts_and_names_the_store(
    target: Path,
) -> None:
    draft_id = _stage_via_cli(target)
    res = CliRunner().invoke(main, ["report", "submit"])
    assert res.exit_code == 0, res.output
    assert draft_id in res.output and "bug" in res.output
    # list mode says WHICH store it is listing (#693) — the store is per-project
    assert str(rep.drafts_dir(target)) in res.output


def test_submit_bare_empty_state_names_the_store(target: Path) -> None:
    res = CliRunner().invoke(main, ["report", "submit"])
    assert res.exit_code == 0, res.output
    assert "No staged report drafts" in res.output
    assert str(rep.drafts_dir(target)) in res.output


def test_submit_refuses_yes(target: Path, monkeypatch) -> None:
    draft_id = _stage_via_cli(target)
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(main, ["report", "submit", draft_id, "--yes"])
    assert res.exit_code != 0
    assert posted["v"] is False
    assert "never runs non-interactively" in res.output
    assert rep.load_staged(target, draft_id) is not None  # draft kept


def test_submit_confirms_posts_stamps_and_cleans(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "# Note\n\nclean note body\n")
    draft_id = _stage_via_cli(target, "--scratchpad", note.name)
    sent = {}

    def fake_post(t, *, title, body, label):
        sent["body"], sent["label"] = body, label
        return f"https://github.com/{t}/issues/702"

    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(rep, "file_report_via_gh", fake_post)
    res = CliRunner().invoke(main, ["report", "submit", draft_id], input="y\n")
    assert res.exit_code == 0, res.output
    assert f"Post as @tester to {REPORT_TARGET}?" in res.output
    # submit posts through the same ensured, namespaced label path (#663)
    assert "clean note body" in sent["body"] and sent["label"] == "report:bug"
    assert "filed:" in res.output and "702" in res.output
    assert "Stamped reported" in res.output
    assert (target / ".pkit" / "scratchpad" / "reported" / note.name).exists()
    assert rep.load_staged(target, draft_id) is None  # stage file removed


def test_submit_decline_keeps_draft_and_posts_nothing(
    target: Path, monkeypatch
) -> None:
    draft_id = _stage_via_cli(target)
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    res = CliRunner().invoke(main, ["report", "submit", draft_id], input="n\n")
    assert res.exit_code == 0, res.output
    assert posted["v"] is False
    assert "draft kept" in res.output
    assert rep.load_staged(target, draft_id) is not None


def test_submit_resurfaces_staged_redaction_warnings(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "path /Users/alice/project leaked\n")
    draft_id = _stage_via_cli(target, "--scratchpad", note.name)
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    # decline the send-anyway prompt: nothing posts, draft survives
    res = CliRunner().invoke(main, ["report", "submit", draft_id], input="n\n")
    assert res.exit_code == 0, res.output
    assert "macOS home path" in res.output
    assert "Send anyway?" in res.output
    assert rep.load_staged(target, draft_id) is not None


def test_submit_posts_overflow_comment_of_oversize_draft(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "z" * 70_000)
    draft_id = _stage_via_cli(target, "--scratchpad", note.name)
    comments = []
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda t, **k: f"https://github.com/{t}/issues/703",
    )
    monkeypatch.setattr(
        rep, "post_issue_comment",
        lambda t, issue, body: comments.append(body) or (True, ""),
    )
    res = CliRunner().invoke(main, ["report", "submit", draft_id], input="y\n")
    assert res.exit_code == 0, res.output
    assert "ONE overflow comment" in res.output  # confirmed as one gesture
    assert len(comments) == 1 and "z" * 70_000 in comments[0]
    assert rep.load_staged(target, draft_id) is None


def test_submit_overflow_failure_fails_closed_and_keeps_draft(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "w" * 70_000)
    draft_id = _stage_via_cli(target, "--scratchpad", note.name)
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda t, **k: f"https://github.com/{t}/issues/704",
    )
    monkeypatch.setattr(
        rep, "post_issue_comment", lambda t, issue, body: (False, "boom")
    )
    res = CliRunner().invoke(main, ["report", "submit", draft_id], input="y\n")
    assert res.exit_code == 0, res.output
    assert "NOT stamped reported" in res.output and "boom" in res.output
    assert "do NOT resubmit" in res.output
    assert rep.load_staged(target, draft_id) is not None  # kept for the text
    assert not (target / ".pkit" / "scratchpad" / "reported" / note.name).exists()


def test_submit_missing_draft_names_where_it_looked(target: Path) -> None:
    # The #693 diagnostic: an id that isn't here must say WHERE "here" is and
    # that drafts are per-project — the draft may well exist under another root.
    res = CliRunner().invoke(main, ["report", "submit", "nope"])
    assert res.exit_code != 0
    assert "no staged draft" in res.output
    assert str(rep.drafts_dir(target)) in res.output
    assert f"project root: {target}" in res.output
    assert "per-project" in res.output
    assert "run submit from that project's root" in res.output.lower()


def test_submit_requires_gh_auth(target: Path) -> None:
    draft_id = _stage_via_cli(target)
    res = CliRunner().invoke(main, ["report", "submit", draft_id])
    assert res.exit_code != 0
    assert "gh auth login" in res.output


# --- URL-path tracking follow-up (#664 / #660 C.7) --------------------

_FOLLOWUP = (
    "after filing in the browser, run: "
    "pkit scratchpad reported send-note <issue-ref>"
)


def _last_line(output: str) -> str:
    return [ln for ln in output.splitlines() if ln.strip()][-1]


def test_url_path_with_note_ends_with_reported_followup(
    target: Path, monkeypatch
) -> None:
    # A browser filing stamps nothing, so a scratchpad-backed --url flow must
    # END with the exact one-command tracking gesture as its LAST line.
    note = _note(target, "# Note\n\nclean\n")
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name, "--url"],
    )
    assert res.exit_code == 0, res.output
    assert _last_line(res.output) == _FOLLOWUP


def test_open_path_with_note_ends_with_reported_followup(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "# Note\n\nclean\n")
    monkeypatch.setattr(rep, "open_in_browser", lambda url: True)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name, "--open"],
    )
    assert res.exit_code == 0, res.output
    assert _last_line(res.output) == _FOLLOWUP  # after the opened-browser note


def test_no_auth_fallback_with_note_ends_with_reported_followup(
    target: Path,
) -> None:
    # gh unauthenticated (the autouse pin): the implicit URL fallback is a
    # URL-path filing too — same required follow-up, same last line.
    note = _note(target, "# Note\n\nclean\n")
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name],
    )
    assert res.exit_code == 0, res.output
    assert _last_line(res.output) == _FOLLOWUP


def test_url_path_without_note_prints_no_followup(target: Path) -> None:
    # nothing attached ⇒ nothing to track ⇒ no follow-up noise
    res = CliRunner().invoke(
        main, ["report", "bug", "--title", "t", "--body", "b", "--url"]
    )
    assert res.exit_code == 0, res.output
    assert "scratchpad reported" not in res.output


def test_api_decline_url_degrade_ends_with_reported_followup(
    target: Path, monkeypatch
) -> None:
    # Declining the API confirm degrades to the printed URL — a degraded
    # outcome that may still be filed in the browser, so it too must end
    # with the follow-up.
    note = _note(target, "# Note\n\nclean\n")
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name],
        input="n\n",
    )
    assert res.exit_code == 0, res.output
    assert "issues/new?" in res.output
    assert _last_line(res.output) == _FOLLOWUP


def test_api_failure_url_degrade_ends_with_reported_followup(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "# Note\n\nclean\n")
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(rep, "file_report_via_gh", lambda *a, **k: None)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name],
        input="y\n",
    )
    assert res.exit_code == 0, res.output
    assert "gh could not file it" in res.output
    assert _last_line(res.output) == _FOLLOWUP


# --- redaction lint on every path (#664 / #660 C.8; COR-043) ----------
# The four compose paths: interactive API (below), --url/--open (below),
# --yes stage (test_yes_stage_carries_redaction_findings_as_header_warnings),
# submit resurface (test_submit_resurfaces_staged_redaction_warnings). The
# staged path's stamp-at-submit is pinned by
# test_submit_confirms_posts_stamps_and_cleans.


def test_interactive_api_path_lints_note_and_gates_on_findings(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "path /Users/alice/project leaked\n")
    posted = {"v": False}
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    monkeypatch.setattr(
        rep, "file_report_via_gh",
        lambda *a, **k: posted.__setitem__("v", True) or "x",
    )
    # decline the edit-or-send-anyway prompt: nothing posts
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name],
        input="n\n",
    )
    assert res.exit_code == 0, res.output
    assert "macOS home path" in res.output
    assert "Send anyway?" in res.output
    assert posted["v"] is False
    assert "Not posted" in res.output


def test_url_path_lints_note_and_surfaces_findings(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "path /Users/alice/project leaked\n")
    monkeypatch.setattr(rep, "gh_authenticated", lambda: True)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name, "--url"],
    )
    assert res.exit_code == 0, res.output
    assert "possible un-redacted content" in res.output
    assert "macOS home path" in res.output


def test_open_path_lints_note_and_surfaces_findings(
    target: Path, monkeypatch
) -> None:
    note = _note(target, "path /Users/alice/project leaked\n")
    monkeypatch.setattr(rep, "open_in_browser", lambda url: True)
    res = CliRunner().invoke(
        main,
        ["report", "feedback", "--title", "t", "--body", "b",
         "--scratchpad", note.name, "--open"],
    )
    assert res.exit_code == 0, res.output
    assert "possible un-redacted content" in res.output
    assert "macOS home path" in res.output


# --- staging round-trip (module level) --------------------------------


def test_stage_and_load_roundtrip_fields(target: Path) -> None:
    payload = SendPayload("the body\n", "the overflow", truncated=True)
    findings = rep.lint_redaction("a /Users/alice path")
    draft = rep.stage_report(
        target, kind="feedback", title="T: tricky title", payload=payload,
        findings=findings, note_path=target / ".pkit/scratchpad/active/n.md",
        project="alpha", workstream="cli",
    )
    loaded = rep.load_staged(target, draft.draft_id)
    assert loaded is not None
    assert loaded.kind == "feedback" and loaded.title == "T: tricky title"
    assert loaded.project == "alpha" and loaded.workstream == "cli"
    assert loaded.note == ".pkit/scratchpad/active/n.md"
    assert loaded.payload.body == "the body\n"
    assert loaded.payload.overflow_comment == "the overflow"
    assert loaded.payload.truncated is True
    assert loaded.warnings == draft.warnings and loaded.warnings


def test_stage_ids_do_not_collide(target: Path) -> None:
    payload = SendPayload("b\n")
    a = rep.stage_report(target, kind="bug", title="t", payload=payload)
    b = rep.stage_report(target, kind="bug", title="t", payload=payload)
    assert a.draft_id != b.draft_id
    assert len(rep.list_staged(target)) == 2
