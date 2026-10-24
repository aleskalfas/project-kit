"""Tests for `_lib/workstream_sync`, what the workstream mutators read and write (#1940).

DEC-018 makes workstreams.yaml the source of truth and the substrate that carries
the axis its projection. These tests pin the shared reads and writes the mutators
compose: the issues that carry a slug on each carriage, the repository's labels,
the board's `Workstream` field and the option lists that change it, and the
rewriting of typed references in files and on GitHub. Every `gh` call is a fake.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.pm_workstream_fakes import FakeBoard, FakeRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import axis_labels, board_fields, substrate_writes, workstream_sync  # noqa: E402

BOARD_CONFIG = {"has_projects_v2_board": True, "projects_v2_board_id": 7}


def _issue(title: str, *labels: str, body: str = "", author: str = "me") -> dict:
    return {"title": title, "labels": list(labels), "body": body, "author": author}


# --- carriers, whatever the carriage ---------------------------------------


def test_carriers_reads_the_kit_label() -> None:
    repo = FakeRepo(issues={1: _issue("One", "workstream:cli"), 2: _issue("Two")})
    read = workstream_sync.carriers(
        "cli", carriage="kit-label", config={}, substrate_map=None, gh_call=repo
    )
    assert read.ok is True
    assert [c.number for c in read.carriers] == [1]


def test_carriers_reads_the_adopters_own_label() -> None:
    sm = axis_labels.SubstrateMap(axes={"workstream": {"label": {"remap": {"cli": "area/cli"}}}})
    repo = FakeRepo(issues={4: _issue("Four", "area/cli"), 5: _issue("Five", "workstream:cli")})
    read = workstream_sync.carriers(
        "cli", carriage="adopter-label", config={}, substrate_map=sm, gh_call=repo
    )
    assert [c.number for c in read.carriers] == [4]


def test_carriers_finds_nothing_for_a_value_the_map_does_not_bind() -> None:
    sm = axis_labels.SubstrateMap(axes={"workstream": {"label": {"remap": {"cli": "area/cli"}}}})
    repo = FakeRepo()
    read = workstream_sync.carriers(
        "docs", carriage="adopter-label", config={}, substrate_map=sm, gh_call=repo
    )
    assert read.ok is True
    assert read.carriers == ()
    assert repo.calls == []


def test_carriers_reads_a_title_prefix() -> None:
    sm = axis_labels.SubstrateMap(
        axes={"workstream": {"title-prefix": {"remap": {"cli": "[CLI]"}}}}
    )

    def gh(cmd, config, *, check=True, **kwargs):
        rows = [{"number": 1, "title": "[CLI] Fix it"}, {"number": 2, "title": "About [CLI]"}]
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(rows))

    read = workstream_sync.carriers(
        "cli", carriage="title", config={}, substrate_map=sm, gh_call=gh
    )
    assert [c.number for c in read.carriers] == [1]


def test_carriers_reads_the_board_cards(monkeypatch) -> None:
    board = FakeBoard(["cli", "docs"], {"I1": (1, "cli"), "I2": (2, "docs"), "I3": (3, "cli")})
    board.install(monkeypatch, board_fields, substrate_writes)
    read = workstream_sync.carriers(
        "cli", carriage="board", config=BOARD_CONFIG, substrate_map=None, gh_call=FakeRepo()
    )
    assert [(c.number, c.item_id) for c in read.carriers] == [(1, "I1"), (3, "I3")]


def test_carriers_fails_when_the_board_cannot_be_read(monkeypatch) -> None:
    FakeBoard(["cli"], fail_reads=True).install(monkeypatch, board_fields, substrate_writes)
    read = workstream_sync.carriers(
        "cli", carriage="board", config=BOARD_CONFIG, substrate_map=None, gh_call=FakeRepo()
    )
    assert read.ok is False
    assert "read:project" in (read.error or "")


def test_carriers_fails_when_the_label_read_fails() -> None:
    def gh(cmd, config, *, check=True, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="HTTP 401")

    read = workstream_sync.carriers(
        "cli", carriage="kit-label", config={}, substrate_map=None, gh_call=gh
    )
    assert read.ok is False
    assert read.error == "HTTP 401"


# --- labels -----------------------------------------------------------------


def test_label_names_are_lower_cased() -> None:
    names, error = workstream_sync.label_names(
        {}, gh_call=FakeRepo(labels={"Workstream:CLI", "bug"})
    )
    assert error is None
    assert names == {"workstream:cli", "bug"}


# --- the board's field ------------------------------------------------------


def test_read_board_field_names_a_board_with_no_workstream_field(monkeypatch) -> None:
    FakeBoard(has_field=False).install(monkeypatch, board_fields, substrate_writes)
    read = workstream_sync.read_board_field(BOARD_CONFIG)
    assert read.field is None and read.error is None
    assert "no field named `Workstream`" in (read.problem or "")


def test_read_board_field_names_a_field_that_is_not_a_single_select(monkeypatch) -> None:
    FakeBoard(field_type="ProjectV2Field").install(monkeypatch, board_fields, substrate_writes)
    read = workstream_sync.read_board_field(BOARD_CONFIG)
    assert "not a single-select" in (read.problem or "")


def _field() -> workstream_sync.BoardField:
    field = workstream_sync.read_board_field(BOARD_CONFIG).field
    assert field is not None
    return field


def test_option_lists_keep_each_option_id(monkeypatch) -> None:
    FakeBoard(["cli", "docs"]).install(monkeypatch, board_fields, substrate_writes)
    field = _field()
    renamed = workstream_sync.options_renaming(field, "cli", "tools")
    assert [(o["id"], o["name"]) for o in renamed] == [("opt_cli", "tools"), ("opt_docs", "docs")]
    assert [o["name"] for o in workstream_sync.options_without(field, ["cli"])] == ["docs"]
    added = workstream_sync.options_adding(field, "infra", "Infrastructure.")
    assert added[-1] == {"name": "infra", "description": "Infrastructure."}


def test_a_renamed_option_keeps_the_cards_value(monkeypatch) -> None:
    board = FakeBoard(["cli"], {"I1": (1, "cli")})
    board.install(monkeypatch, board_fields, substrate_writes)
    field = _field()
    result = workstream_sync.write_options(
        BOARD_CONFIG, field, workstream_sync.options_renaming(field, "cli", "tools")
    )
    assert result.ok is True
    assert board.option_names() == ["tools"]
    assert board.card_option("I1") == "tools"


# --- references -------------------------------------------------------------


def _git_repo(root: Path, files: dict[str, str]) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)


def test_files_referencing_reads_tracked_files_only(tmp_path) -> None:
    _git_repo(tmp_path, {"a.md": "see workstream:cli\n", "b.md": "workstream:cli-tools\n"})
    (tmp_path / "untracked.md").write_text("workstream:cli\n", encoding="utf-8")
    paths, error = workstream_sync.files_referencing(tmp_path, "workstream:cli")
    assert error is None
    assert [p.name for p in paths] == ["a.md"]


def test_files_referencing_leaves_the_pkit_tree_and_the_changelog(tmp_path) -> None:
    """Core-owned files and history keep the names they were written under."""
    (tmp_path / ".pkit" / "decisions").mkdir(parents=True)
    (tmp_path / ".changes").mkdir()
    _git_repo(
        tmp_path,
        {
            ".pkit/decisions/DEC-001.md": "workstream:cli\n",
            ".changes/a.yaml": "body: workstream:cli\n",
            "CHANGELOG.md": "- workstream:cli\n",
            "docs.md": "workstream:cli\n",
        },
    )
    paths, _error = workstream_sync.files_referencing(tmp_path, "workstream:cli")
    assert [p.name for p in paths] == ["docs.md"]


def test_files_referencing_skips_a_file_reached_through_a_link_out(tmp_path) -> None:
    root, outside = tmp_path / "repo", tmp_path / "outside"
    (root / "docs").mkdir(parents=True)
    outside.mkdir()
    _git_repo(root, {"docs/a.md": "workstream:cli\n"})
    # The tracked folder is replaced by a link to a folder outside the repository.
    (outside / "a.md").write_text("workstream:cli\n", encoding="utf-8")
    (root / "docs" / "a.md").unlink()
    (root / "docs").rmdir()
    (root / "docs").symlink_to(outside, target_is_directory=True)
    paths, _error = workstream_sync.files_referencing(root, "workstream:cli")
    assert paths == []


def test_confirm_each_declines_without_a_shell_and_yes(monkeypatch) -> None:
    class _NoShell:
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(sys, "stdin", _NoShell())
    assert workstream_sync.confirm_each(False)("Rewrite? ") is False
    assert workstream_sync.confirm_each(True)("Rewrite? ") is True
    assert workstream_sync.references_need_yes(False, False) is True
    assert workstream_sync.references_need_yes(True, False) is False
    assert workstream_sync.references_need_yes(False, True) is False


def test_rewrite_everywhere_rewrites_files_bodies_and_own_comments(tmp_path) -> None:
    _git_repo(tmp_path, {"a.md": "Filed as [workstream:cli].\n", "b.md": "workstream:cli\n"})
    repo = FakeRepo(
        issues={7: _issue("Seven", body="Part of workstream:cli.", author="someone")},
        comments={
            7: [
                {"id": 70, "body": "moving to workstream:cli", "login": "me"},
                {"id": 71, "body": "workstream:cli please", "login": "someone"},
            ]
        },
        login="me",
    )
    asked: list[str] = []

    def confirm(question: str) -> bool:
        asked.append(question)
        return "b.md" not in question

    outcome = workstream_sync.rewrite_everywhere(
        "workstream:cli",
        target=lambda _number, _where: "workstream:tools",
        confirm=confirm,
        root=tmp_path,
        config={},
        gh_call=repo,
        stamp=lambda text: text + "\n<!-- stamped -->",
        cwd=tmp_path,
    )
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "Filed as [workstream:tools].\n"
    # A declined file is left as it was.
    assert (tmp_path / "b.md").read_text(encoding="utf-8") == "workstream:cli\n"
    assert repo.patched["repos/{owner}/{repo}/issues/7"] == (
        "Part of workstream:tools.\n<!-- stamped -->"
    )
    assert repo.patched["repos/{owner}/{repo}/issues/comments/70"] == "moving to workstream:tools"
    # Someone else's comment is left without admin rights, with a reason.
    assert "repos/{owner}/{repo}/issues/comments/71" not in repo.patched
    assert any("71" in line and "admin" in line for line in outcome.skipped)
    assert any("b.md: declined" in line for line in outcome.skipped)
    assert outcome.failed == []


def test_rewrite_everywhere_edits_others_comments_with_admin_rights(tmp_path) -> None:
    _git_repo(tmp_path, {"README.md": "nothing here\n"})
    repo = FakeRepo(
        issues={7: _issue("Seven")},
        comments={7: [{"id": 71, "body": "workstream:cli please", "login": "someone"}]},
        admin=True,
    )
    workstream_sync.rewrite_everywhere(
        "workstream:cli",
        target=lambda _number, _where: "workstream:tools",
        confirm=lambda _question: True,
        root=tmp_path,
        config={},
        gh_call=repo,
    )
    assert repo.patched["repos/{owner}/{repo}/issues/comments/71"] == "workstream:tools please"


def test_rewrite_everywhere_leaves_a_reference_with_no_target(tmp_path) -> None:
    _git_repo(tmp_path, {"a.md": "workstream:cli\n"})
    outcome = workstream_sync.rewrite_everywhere(
        "workstream:cli",
        target=lambda _number, _where: None,
        confirm=lambda _question: True,
        root=tmp_path,
        config={},
        gh_call=FakeRepo(),
    )
    assert (tmp_path / "a.md").read_text(encoding="utf-8") == "workstream:cli\n"
    assert outcome.skipped == ["a.md: no workstream chosen"]
