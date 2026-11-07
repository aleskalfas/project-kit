"""Tests for scratchpad stamping, state transitions and the `scratchpad` member of
`pkit validate` (per COR-012)."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import click
import pytest

from project_kit import scratchpads


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal project tree with `.pkit/scratchpad/{active,done,dropped}/`."""
    scratchpad = tmp_path / ".pkit" / "scratchpad"
    for state in ("active", "done", "dropped"):
        (scratchpad / state).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin `_today()` and `_today_date()` for deterministic dates."""
    monkeypatch.setattr(scratchpads, "_today", lambda: "2026-05-12")
    monkeypatch.setattr(scratchpads, "_today_date", lambda: _dt.date(2026, 5, 12))


@pytest.fixture(autouse=True)
def fixed_git_author(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin git-config lookups so authors are deterministic."""

    def _fake_git_config(key: str) -> str:
        return {"user.name": "Test Author", "user.email": "test@example.com"}.get(key, "")

    monkeypatch.setattr(scratchpads, "_git_config", _fake_git_config)


# --- stamp_new_scratchpad --------------------------------------------


def test_stamp_new_scratchpad_creates_file_in_active(kit_target: Path) -> None:
    target = scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    assert target.name == "2026-05-12-my-note.md"
    assert target.parent == kit_target / ".pkit" / "scratchpad" / "active"
    assert target.is_file()


def test_stamp_new_scratchpad_seeds_frontmatter_and_h1(kit_target: Path) -> None:
    target = scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    content = target.read_text(encoding="utf-8")
    assert "authors:\n  - Test Author <test@example.com>" in content
    assert "started: 2026-05-12" in content
    assert "\n# My note\n" in content


def test_stamp_new_scratchpad_rejects_invalid_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match=r"slug must be kebab-case"):
        scratchpads.stamp_new_scratchpad(kit_target, slug="Invalid_Slug")


def test_stamp_new_scratchpad_refuses_existing_filename(kit_target: Path) -> None:
    scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    with pytest.raises(click.ClickException, match=r"already exists"):
        scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")


def test_stamp_new_scratchpad_refuses_slug_present_in_done(kit_target: Path) -> None:
    done = kit_target / ".pkit" / "scratchpad" / "done"
    (done / "2026-04-01-already-used.md").write_text("---\n---\n# already-used\n", encoding="utf-8")
    with pytest.raises(click.ClickException, match=r"already used"):
        scratchpads.stamp_new_scratchpad(kit_target, slug="already-used")


def test_stamp_new_scratchpad_dry_run_writes_nothing(kit_target: Path) -> None:
    target = scratchpads.stamp_new_scratchpad(kit_target, slug="my-note", dry_run=True)
    assert not target.exists()


def test_stamp_new_scratchpad_refuses_when_active_missing(tmp_path: Path) -> None:
    # No .pkit/scratchpad/active/ at all.
    with pytest.raises(click.ClickException, match=r"does not exist"):
        scratchpads.stamp_new_scratchpad(tmp_path, slug="my-note")


# --- transition_to_done ---------------------------------------------


def test_transition_to_done_moves_file(kit_target: Path) -> None:
    scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    src, dst = scratchpads.transition_to_done(kit_target, slug="my-note")
    assert not src.exists()
    assert dst.is_file()
    assert dst.parent == kit_target / ".pkit" / "scratchpad" / "done"
    assert dst.name == src.name


def test_transition_to_done_appends_retired_and_produced(kit_target: Path) -> None:
    scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    _src, dst = scratchpads.transition_to_done(
        kit_target, slug="my-note", produced=("COR-013", ".pkit/agents/README.md")
    )
    content = dst.read_text(encoding="utf-8")
    assert "retired: 2026-05-12" in content
    # Quoted strings would break round-tripping; expect bare scalars.
    assert "retired: '2026-05-12'" not in content
    assert "produced:\n  - COR-013\n  - .pkit/agents/README.md" in content


def test_transition_to_done_without_produced_omits_field(kit_target: Path) -> None:
    scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    _src, dst = scratchpads.transition_to_done(kit_target, slug="my-note")
    content = dst.read_text(encoding="utf-8")
    assert "retired: 2026-05-12" in content
    assert "produced:" not in content


def test_transition_to_done_resolves_by_full_filename(kit_target: Path) -> None:
    scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    _src, dst = scratchpads.transition_to_done(kit_target, slug="2026-05-12-my-note.md")
    assert dst.is_file()


def test_transition_to_done_refuses_unknown_slug(kit_target: Path) -> None:
    with pytest.raises(click.ClickException, match=r"no active or reported scratchpad note"):
        scratchpads.transition_to_done(kit_target, slug="missing")


def test_transition_to_done_dry_run_does_not_modify(kit_target: Path) -> None:
    src_target = scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    _src, dst = scratchpads.transition_to_done(kit_target, slug="my-note", dry_run=True)
    assert src_target.is_file(), "dry-run must not remove the source"
    assert not dst.exists(), "dry-run must not create the destination"


# --- transition_to_dropped ------------------------------------------


def test_transition_to_dropped_moves_file(kit_target: Path) -> None:
    scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    src, dst = scratchpads.transition_to_dropped(kit_target, slug="my-note")
    assert not src.exists()
    assert dst.is_file()
    assert dst.parent == kit_target / ".pkit" / "scratchpad" / "dropped"


def test_transition_to_dropped_appends_retired_no_produced(kit_target: Path) -> None:
    scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    _src, dst = scratchpads.transition_to_dropped(kit_target, slug="my-note")
    content = dst.read_text(encoding="utf-8")
    assert "retired: 2026-05-12" in content
    assert "produced:" not in content


def test_transition_to_dropped_dry_run_does_not_modify(kit_target: Path) -> None:
    src_target = scratchpads.stamp_new_scratchpad(kit_target, slug="my-note")
    _src, dst = scratchpads.transition_to_dropped(kit_target, slug="my-note", dry_run=True)
    assert src_target.is_file()
    assert not dst.exists()


# --- outcome: a note lies in one state folder (COR-012) -------------


def _note(kit_target: Path, state: str, name: str) -> None:
    folder = kit_target / ".pkit" / "scratchpad" / state
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("---\nstarted: 2026-05-12\n---\n\n# A note\n", encoding="utf-8")


def test_outcome_passes_when_each_slug_is_in_one_state(kit_target: Path) -> None:
    _note(kit_target, "active", "2026-05-12-open-question.md")
    _note(kit_target, "done", "2026-04-01-settled-question.md")
    _note(kit_target, "dropped", "2026-03-01-failed-idea.md")
    outcome = scratchpads.outcome(kit_target)
    assert outcome.findings == ()
    assert outcome.summary == ("3 scratchpad note(s) checked; 0 error(s).",)


def test_outcome_reports_a_slug_in_more_than_one_state_once_naming_every_file(
    kit_target: Path,
) -> None:
    _note(kit_target, "active", "2026-09-30-review-load.md")
    _note(kit_target, "reported", "2026-10-02-review-load.md")
    _note(kit_target, "done", "2026-09-30-review-load.md")
    _note(kit_target, "done", "2026-05-12-other-note.md")
    outcome = scratchpads.outcome(kit_target)
    [finding] = outcome.findings
    assert finding.severity.fails
    assert finding.location == ".pkit/scratchpad :: review-load"
    assert finding.message.startswith(
        "slug 'review-load' is in 3 state folders: "
        ".pkit/scratchpad/active/2026-09-30-review-load.md, "
        ".pkit/scratchpad/reported/2026-10-02-review-load.md, "
        ".pkit/scratchpad/done/2026-09-30-review-load.md. "
    )
    assert "(COR-012)" in finding.message
    assert outcome.summary == ("4 scratchpad note(s) checked; 1 error(s).",)


def test_outcome_leaves_two_notes_of_one_slug_in_one_folder_alone(kit_target: Path) -> None:
    _note(kit_target, "active", "2026-05-12-cache-layer.md")
    _note(kit_target, "active", "2026-06-01-cache-layer.md")
    assert scratchpads.outcome(kit_target).findings == ()


def test_outcome_compares_whole_slugs_and_reads_only_md_files(kit_target: Path) -> None:
    _note(kit_target, "active", "2026-06-03-layer.md")
    _note(kit_target, "done", "2026-06-03-cache-layer.md")  # ends in `-layer`, another slug
    _note(kit_target, "done", "2026-06-03-layer.tsv")  # not a note
    (kit_target / ".pkit" / "scratchpad" / "dropped" / "2026-06-03-layer.md").mkdir()
    outcome = scratchpads.outcome(kit_target)
    assert outcome.findings == ()
    assert outcome.summary == ("2 scratchpad note(s) checked; 0 error(s).",)


def test_outcome_without_a_scratchpad_area_checks_nothing(tmp_path: Path) -> None:
    outcome = scratchpads.outcome(tmp_path)
    assert outcome.findings == ()
    assert outcome.summary == ("0 scratchpad note(s) checked; 0 error(s).",)
