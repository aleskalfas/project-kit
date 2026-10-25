"""Tests for the workstream lifecycle scripts' file-mutation logic.

Covers rename/edit/merge/split/remove via their file-write helpers.
The gh subprocess wrappers are not unit-tested (thin pass-throughs).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from tests.pm_workstream_fakes import FakeBoard, FakeRepo, stage_project

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


def _load(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    module_name = f"pm_{name}_under_test"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rn():
    return _load("rename-workstream")


# --- rename ----------------------------------------------------------


def test_rename_in_file_list_form(rn, tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\nworkstreams:\n  - cli\n  - schemas\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ok = rn._rename_in_file(yaml, data, "cli", "cli-tools", path)
    assert ok is True
    text = path.read_text(encoding="utf-8")
    assert "cli-tools" in text
    assert "schemas" in text
    # Old slug `cli` should not appear as a standalone list item.
    assert "\n- cli\n" not in text and "  - cli\n" not in text


def test_rename_in_file_mapping_form(rn, tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\n"
        "workstreams:\n"
        "  cli:\n    name: cli\n    status: active\n"
        "  schemas:\n    name: schemas\n    status: active\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ok = rn._rename_in_file(yaml, data, "cli", "agent-platform", path)
    assert ok is True
    text = path.read_text(encoding="utf-8")
    assert "agent-platform:" in text
    assert "schemas:" in text


# --- end-to-end via test fixture: parse and verify state -------------


def test_remove_file_mutation_mapping_form(tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\n"
        "workstreams:\n"
        "  cli:\n    name: cli\n    status: active\n"
        "  schemas:\n    name: schemas\n    status: active\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ws = data["workstreams"]
    ws.pop("cli")
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    text = path.read_text(encoding="utf-8")
    assert "schemas:" in text
    assert "cli:" not in text


def test_merge_file_mutation_list_form(tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\nworkstreams:\n  - cli\n  - cli-old\n  - other\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ws = data["workstreams"]
    losers = {"cli-old"}
    data["workstreams"] = [item for item in ws if item not in losers]
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    text = path.read_text(encoding="utf-8")
    assert "cli\n" in text
    assert "other\n" in text
    assert "cli-old" not in text


def test_split_file_mutation_mapping_form(tmp_path) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    path = tmp_path / "workstreams.yaml"
    path.write_text(
        "schema_version: 1\nworkstreams:\n  cli:\n    name: cli\n    status: active\n",
        encoding="utf-8",
    )
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    ws = data["workstreams"]
    ws.pop("cli")
    for slug in ["cli-tools", "cli-rendering"]:
        ws[slug] = {"name": slug, "status": "active"}
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)
    text = path.read_text(encoding="utf-8")
    assert "cli-tools:" in text
    assert "cli-rendering:" in text
    assert "  cli:" not in text


# --- edit ------------------------------------------------------------


@pytest.fixture(scope="module")
def ew():
    return _load("edit-workstream")


def test_edit_workstream_no_args_returns_usage_error(ew, monkeypatch) -> None:
    """Calling main with no edit-args should exit 2 (usage error).

    We bypass argparse + membership checks by short-circuiting the
    capability-root resolution to a non-existent path. The first
    return is the no-edit-args check.
    """
    monkeypatch.setattr(sys, "argv", ["edit-workstream", "cli"])
    rc = ew.main()
    assert rc == 2


# =========================================================================
# main(): each command does what DEC-018 decides for it (#1940)
# =========================================================================

TWO = (
    "schema_version: 1\nworkstreams:\n"
    "  cli:\n    name: cli\n    status: active\n"
    "  old:\n    name: old\n    status: active\n"
)
ONE = "schema_version: 1\nworkstreams:\n  cli:\n    name: cli\n    status: active\n"


@pytest.fixture(scope="module")
def mw():
    return _load("merge-workstream")


@pytest.fixture(scope="module")
def sw():
    return _load("split-workstream")


@pytest.fixture(scope="module")
def rw():
    return _load("remove-workstream")


@pytest.fixture
def seams():
    """The board read and write seams, as the loaded scripts import them."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import board_fields, substrate_writes

    return board_fields, substrate_writes


class _Shell:
    """An interactive standard input, for the prompts a script asks only there."""

    def isatty(self) -> bool:
        return True


def _run(module, monkeypatch, cap_root: Path, name: str, *argv: str, yes: bool = True) -> int:
    # The invoker's login, without asking GitHub for it.
    monkeypatch.setenv("PM_INVOKER_LOGIN", "me")
    args = [f"{name}.py", *argv, "--capability-root", str(cap_root)]
    monkeypatch.setattr(sys, "argv", args + (["--yes"] if yes else []))
    return module.main()


def _file(cap_root: Path) -> str:
    return (cap_root / "project" / "workstreams.yaml").read_text(encoding="utf-8")


def _issue(title: str, *labels: str, body: str = "") -> dict:
    return {"title": title, "labels": list(labels), "body": body, "author": "me"}


def _git(root: Path, files: dict[str, str]) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)


# --- edit ------------------------------------------------------------------


def test_edit_refuses_a_description_over_200_chars(ew, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    rc = _run(ew, monkeypatch, tmp_path, "edit-workstream", "cli", "--description", "d" * 250)
    assert rc == 1
    assert _file(tmp_path) == ONE


def test_edit_refuses_a_multi_line_name(ew, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    assert _run(ew, monkeypatch, tmp_path, "edit-workstream", "cli", "--name", "a\nb") == 1
    assert _file(tmp_path) == ONE


# --- rename ----------------------------------------------------------------


@pytest.mark.parametrize("new", ["a--b", "a" * 41])
def test_rename_checks_the_new_slug_in_full(rn, tmp_path, monkeypatch, new) -> None:
    stage_project(tmp_path, ONE)
    repo = FakeRepo(labels={"workstream:cli"})
    monkeypatch.setattr(rn, "gh_run", repo)
    assert _run(rn, monkeypatch, tmp_path, "rename-workstream", "cli", new) == 1
    assert _file(tmp_path) == ONE
    assert repo.calls == []


def test_rename_refuses_when_both_labels_exist_and_changes_nothing(
    rn, tmp_path, monkeypatch
) -> None:
    """The reported gap: the entry was renamed, the label rename failed, and the
    command exited 0 with the issues still on the old label."""
    stage_project(tmp_path, ONE)
    repo = FakeRepo(
        labels={"workstream:cli", "workstream:tools"},
        issues={1: _issue("One", "workstream:cli")},
    )
    monkeypatch.setattr(rn, "gh_run", repo)
    assert _run(rn, monkeypatch, tmp_path, "rename-workstream", "cli", "tools") == 1
    assert _file(tmp_path) == ONE
    assert repo.mutations() == []


def test_rename_renames_the_label_and_the_entry(rn, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = FakeRepo(labels={"workstream:cli"}, issues={1: _issue("One", "workstream:cli")})
    monkeypatch.setattr(rn, "gh_run", repo)
    assert _run(rn, monkeypatch, tmp_path, "rename-workstream", "cli", "tools") == 0
    assert repo.labels == {"workstream:tools"}
    assert repo.issues[1]["labels"] == ["workstream:tools"]
    assert "tools:" in _file(tmp_path) and "cli:" not in _file(tmp_path)


def test_rename_creates_the_new_label_where_the_old_one_is_missing(
    rn, tmp_path, monkeypatch
) -> None:
    stage_project(tmp_path, ONE)
    repo = FakeRepo()
    monkeypatch.setattr(rn, "gh_run", repo)
    assert _run(rn, monkeypatch, tmp_path, "rename-workstream", "cli", "tools") == 0
    assert repo.labels == {"workstream:tools"}


def test_rename_leaves_the_file_when_the_label_is_not_renamed(rn, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = FakeRepo(labels={"workstream:cli"})

    def failing(cmd, config, **kwargs):
        if cmd[1:3] == ["label", "edit"]:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="HTTP 502")
        return repo(cmd, config, **kwargs)

    monkeypatch.setattr(rn, "gh_run", failing)
    assert _run(rn, monkeypatch, tmp_path, "rename-workstream", "cli", "tools") == 3
    assert _file(tmp_path) == ONE


def test_rename_renames_the_board_option_keeping_each_cards_value(
    rn, tmp_path, monkeypatch, seams
) -> None:
    stage_project(tmp_path, ONE, board=True)
    board = FakeBoard(["cli", "docs"], {"I1": (1, "cli")})
    board.install(monkeypatch, *seams)
    monkeypatch.setattr(rn, "gh_run", FakeRepo())
    assert _run(rn, monkeypatch, tmp_path, "rename-workstream", "cli", "tools") == 0
    assert board.option_names() == ["tools", "docs"]
    assert board.card_option("I1") == "tools"
    assert "tools:" in _file(tmp_path)


def test_rename_refuses_when_the_board_offers_both(rn, tmp_path, monkeypatch, seams) -> None:
    stage_project(tmp_path, ONE, board=True)
    board = FakeBoard(["cli", "tools"])
    board.install(monkeypatch, *seams)
    monkeypatch.setattr(rn, "gh_run", FakeRepo())
    assert _run(rn, monkeypatch, tmp_path, "rename-workstream", "cli", "tools") == 1
    assert board.writes == []
    assert _file(tmp_path) == ONE


# --- merge -----------------------------------------------------------------

MERGE_OLD = ("merge-workstream", "--survivor", "cli", "old")


def test_merge_rewrites_references_by_default(mw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, TWO)
    _git(tmp_path, {"NOTES.md": "Filed under [workstream:old].\n"})
    repo = FakeRepo(
        labels={"workstream:cli", "workstream:old"},
        issues={1: _issue("One", "workstream:old", body="Part of workstream:old.")},
    )
    monkeypatch.setattr(mw, "gh_run", repo)
    rc = _run(mw, monkeypatch, tmp_path, "merge-workstream", "--survivor", "cli", "old")
    assert rc == 0
    assert repo.issues[1]["labels"] == ["workstream:cli"]
    assert "workstream:old" not in repo.labels
    assert "old:" not in _file(tmp_path)
    assert (tmp_path / "NOTES.md").read_text(encoding="utf-8") == "Filed under [workstream:cli].\n"
    body = repo.patched["repos/{owner}/{repo}/issues/1"]
    assert body.startswith("Part of workstream:cli.")
    assert "pkit-provenance:start" in body  # an issue body the script edits is stamped


def test_merge_without_a_shell_or_yes_refuses_before_any_change(mw, tmp_path, monkeypatch) -> None:
    """References are confirmed one by one by default; with no shell to ask and
    no --yes, none could be, so the merge refuses up front."""
    stage_project(tmp_path, TWO)
    repo = FakeRepo(
        labels={"workstream:cli", "workstream:old"}, issues={1: _issue("One", "workstream:old")}
    )
    monkeypatch.setattr(mw, "gh_run", repo)
    rc = _run(mw, monkeypatch, tmp_path, *MERGE_OLD, yes=False)
    assert rc == 1
    assert repo.calls == []
    assert "old:" in _file(tmp_path)


def test_merge_skip_references_leaves_them(mw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, TWO)
    _git(tmp_path, {"NOTES.md": "workstream:old\n"})
    repo = FakeRepo(labels={"workstream:cli", "workstream:old"})
    monkeypatch.setattr(mw, "gh_run", repo)
    rc = _run(mw, monkeypatch, tmp_path, *MERGE_OLD, "--skip-references")
    assert rc == 0
    assert (tmp_path / "NOTES.md").read_text(encoding="utf-8") == "workstream:old\n"
    assert repo.patched == {}


def test_merge_keeps_a_loser_whose_issues_did_not_all_move(mw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, TWO)
    repo = FakeRepo(
        labels={"workstream:cli", "workstream:old"},
        issues={1: _issue("One", "workstream:old"), 2: _issue("Two", "workstream:old")},
        fail_edit={2},
    )
    monkeypatch.setattr(mw, "gh_run", repo)
    rc = _run(mw, monkeypatch, tmp_path, *MERGE_OLD, "--skip-references")
    assert rc == 3
    assert "old:" in _file(tmp_path)
    assert "workstream:old" in repo.labels


def test_merge_keeps_a_loser_whose_label_was_not_deleted(mw, tmp_path, monkeypatch) -> None:
    """Every issue moved but the label's delete failed: the file keeps the
    loser, so running the merge again deletes the label (#1940)."""
    stage_project(tmp_path, TWO)
    repo = FakeRepo(
        labels={"workstream:cli", "workstream:old"},
        issues={1: _issue("One", "workstream:old")},
        fail_delete={"workstream:old"},
    )
    monkeypatch.setattr(mw, "gh_run", repo)
    rc = _run(mw, monkeypatch, tmp_path, *MERGE_OLD, "--skip-references")
    assert rc == 3
    assert repo.issues[1]["labels"] == ["workstream:cli"]
    assert "old:" in _file(tmp_path)
    repo.fail_delete.clear()
    rc = _run(mw, monkeypatch, tmp_path, *MERGE_OLD, "--skip-references")
    assert rc == 0
    assert "workstream:old" not in repo.labels
    assert "old:" not in _file(tmp_path)


def test_merge_moves_the_board_cards_and_drops_the_loser_option(
    mw, tmp_path, monkeypatch, seams
) -> None:
    stage_project(tmp_path, TWO, board=True)
    board = FakeBoard(["cli", "old"], {"I1": (1, "old"), "I2": (2, "cli")})
    board.install(monkeypatch, *seams)
    monkeypatch.setattr(mw, "gh_run", FakeRepo())
    rc = _run(mw, monkeypatch, tmp_path, *MERGE_OLD, "--skip-references")
    assert rc == 0
    assert board.card_option("I1") == "cli"
    assert board.card_option("I2") == "cli"
    assert board.option_names() == ["cli"]
    assert "old:" not in _file(tmp_path)


def test_merge_adds_the_survivor_option_the_board_lacks(mw, tmp_path, monkeypatch, seams) -> None:
    stage_project(tmp_path, TWO, board=True)
    board = FakeBoard(["old"], {"I1": (1, "old")})
    board.install(monkeypatch, *seams)
    monkeypatch.setattr(mw, "gh_run", FakeRepo())
    rc = _run(mw, monkeypatch, tmp_path, *MERGE_OLD, "--skip-references")
    assert rc == 0
    assert board.option_names() == ["cli"]
    assert board.card_option("I1") == "cli"


# --- split -----------------------------------------------------------------


@pytest.mark.parametrize("bad", ["a--b", "a" * 41])
def test_split_checks_each_new_slug_in_full(sw, tmp_path, monkeypatch, bad) -> None:
    stage_project(tmp_path, ONE)
    repo = FakeRepo()
    monkeypatch.setattr(sw, "gh_run", repo)
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", bad,
        "--into", "tools",
    )  # fmt: skip
    assert rc == 1
    assert repo.calls == []


def _split_repo() -> FakeRepo:
    return FakeRepo(
        labels={"workstream:cli"},
        issues={1: _issue("One", "workstream:cli"), 2: _issue("Two", "workstream:cli")},
    )


def test_split_asks_of_each_issue_where_it_moves(sw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = _split_repo()
    monkeypatch.setattr(sw, "gh_run", repo)
    monkeypatch.setattr(sys, "stdin", _Shell())
    replies = iter(["1", "cli-rendering", "y"])
    asked: list[str] = []

    def answer(prompt: str) -> str:
        asked.append(prompt)
        return next(replies)

    monkeypatch.setattr("builtins.input", answer)
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", "cli-tools",
        "--into", "cli-rendering", yes=False,
    )  # fmt: skip
    assert rc == 0
    assert asked[0].startswith("#1 One") and asked[1].startswith("#2 Two")
    assert repo.issues[1]["labels"] == ["workstream:cli-tools"]
    assert repo.issues[2]["labels"] == ["workstream:cli-rendering"]
    assert "workstream:cli" not in repo.labels
    assert "cli-tools:" in _file(tmp_path) and "  cli:" not in _file(tmp_path)


def test_split_refuses_an_untriaged_issue_and_changes_nothing(sw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = _split_repo()
    monkeypatch.setattr(sw, "gh_run", repo)
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", "cli-tools",
        "--into", "cli-rendering", "--assign", "1=cli-tools",
    )  # fmt: skip
    assert rc == 1
    assert repo.mutations() == []
    assert _file(tmp_path) == ONE


def test_split_takes_assign_and_default_without_a_shell(sw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = _split_repo()
    monkeypatch.setattr(sw, "gh_run", repo)
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", "cli-tools",
        "--into", "cli-rendering", "--assign", "2=cli-tools", "--default", "cli-rendering",
    )  # fmt: skip
    assert rc == 0
    assert repo.issues[1]["labels"] == ["workstream:cli-rendering"]
    assert repo.issues[2]["labels"] == ["workstream:cli-tools"]


def test_split_refuses_an_assign_for_an_issue_of_another_workstream(
    sw, tmp_path, monkeypatch
) -> None:
    stage_project(tmp_path, ONE)
    repo = _split_repo()
    monkeypatch.setattr(sw, "gh_run", repo)
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", "cli-tools",
        "--into", "cli-rendering", "--assign", "9=cli-tools", "--default", "cli-rendering",
    )  # fmt: skip
    assert rc == 1
    assert repo.mutations() == []


def test_split_include_github_bodies_rewrites_each_reference_to_its_answer(
    sw, tmp_path, monkeypatch
) -> None:
    stage_project(tmp_path, ONE)
    _git(tmp_path, {"NOTES.md": "workstream:cli\n"})
    repo = _split_repo()
    repo.issues[1]["body"] = "Part of workstream:cli."
    monkeypatch.setattr(sw, "gh_run", repo)
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", "cli-tools",
        "--into", "cli-rendering", "--assign", "1=cli-tools", "--default", "cli-rendering",
        "--include-github-bodies",
    )  # fmt: skip
    assert rc == 0
    assert repo.patched["repos/{owner}/{repo}/issues/1"].startswith("Part of workstream:cli-tools.")
    # A file is on no issue, so it takes --default.
    assert (tmp_path / "NOTES.md").read_text(encoding="utf-8") == "workstream:cli-rendering\n"


def test_split_include_github_bodies_without_a_shell_or_yes_refuses(
    sw, tmp_path, monkeypatch
) -> None:
    stage_project(tmp_path, ONE)
    repo = _split_repo()
    monkeypatch.setattr(sw, "gh_run", repo)
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", "cli-tools",
        "--into", "cli-rendering", "--default", "cli-rendering", "--include-github-bodies",
        yes=False,
    )  # fmt: skip
    assert rc == 1
    assert repo.calls == []


def test_split_without_include_github_bodies_rewrites_nothing(sw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = _split_repo()
    monkeypatch.setattr(sw, "gh_run", repo)
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", "cli-tools",
        "--into", "cli-rendering", "--default", "cli-rendering",
    )  # fmt: skip
    assert rc == 0
    assert repo.patched == {}


def test_split_on_a_board_moves_each_card_to_its_answer(sw, tmp_path, monkeypatch, seams) -> None:
    stage_project(tmp_path, ONE, board=True)
    board = FakeBoard(["cli", "docs"], {"I1": (1, "cli"), "I2": (2, "cli"), "I3": (3, "docs")})
    board.install(monkeypatch, *seams)
    monkeypatch.setattr(sw, "gh_run", FakeRepo())
    rc = _run(
        sw, monkeypatch, tmp_path, "split-workstream", "--source", "cli", "--into", "cli-tools",
        "--into", "cli-rendering", "--assign", "1=cli-tools", "--default", "cli-rendering",
    )  # fmt: skip
    assert rc == 0
    assert board.card_option("I1") == "cli-tools"
    assert board.card_option("I2") == "cli-rendering"
    assert board.card_option("I3") == "docs"
    assert board.option_names() == ["docs", "cli-tools", "cli-rendering"]


# --- remove ----------------------------------------------------------------


def test_remove_with_skip_label_refuses_while_issues_carry_the_label(
    rw, tmp_path, monkeypatch
) -> None:
    """The reported failing example: `remove-workstream cli --skip-label --yes`
    removed `cli` while issues still carried `workstream:cli`."""
    stage_project(tmp_path, ONE)
    repo = FakeRepo(labels={"workstream:cli"}, issues={1: _issue("One", "workstream:cli")})
    monkeypatch.setattr(rw, "gh_run", repo)
    assert _run(rw, monkeypatch, tmp_path, "remove-workstream", "cli", "--skip-label") == 1
    assert _file(tmp_path) == ONE
    assert repo.mutations() == []


def test_remove_refuses_while_board_cards_carry_it(rw, tmp_path, monkeypatch, seams) -> None:
    stage_project(tmp_path, ONE, board=True)
    FakeBoard(["cli"], {"I1": (1, "cli")}).install(monkeypatch, *seams)
    monkeypatch.setattr(rw, "gh_run", FakeRepo())
    assert _run(rw, monkeypatch, tmp_path, "remove-workstream", "cli") == 1
    assert _file(tmp_path) == ONE


def test_remove_refuses_when_the_count_cannot_be_read(rw, tmp_path, monkeypatch, seams) -> None:
    stage_project(tmp_path, ONE, board=True)
    FakeBoard(["cli"], fail_reads=True).install(monkeypatch, *seams)
    monkeypatch.setattr(rw, "gh_run", FakeRepo())
    assert _run(rw, monkeypatch, tmp_path, "remove-workstream", "cli") == 3
    assert _file(tmp_path) == ONE


def test_remove_removes_a_workstream_no_issue_carries(rw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = FakeRepo(labels={"workstream:cli"})
    monkeypatch.setattr(rw, "gh_run", repo)
    assert _run(rw, monkeypatch, tmp_path, "remove-workstream", "cli") == 0
    assert "cli:" not in _file(tmp_path)
    assert repo.labels == set()


def test_remove_leaves_the_file_when_the_label_is_not_deleted(rw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = FakeRepo(labels={"workstream:cli"})

    def failing(cmd, config, **kwargs):
        if cmd[1:3] == ["label", "delete"]:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="HTTP 502")
        return repo(cmd, config, **kwargs)

    monkeypatch.setattr(rw, "gh_run", failing)
    assert _run(rw, monkeypatch, tmp_path, "remove-workstream", "cli") == 3
    assert _file(tmp_path) == ONE


def test_remove_force_passes_the_precondition(rw, tmp_path, monkeypatch) -> None:
    stage_project(tmp_path, ONE)
    repo = FakeRepo(labels={"workstream:cli"}, issues={1: _issue("One", "workstream:cli")})
    monkeypatch.setattr(rw, "gh_run", repo)
    assert _run(rw, monkeypatch, tmp_path, "remove-workstream", "cli", "--force") == 0
    assert "cli:" not in _file(tmp_path)
