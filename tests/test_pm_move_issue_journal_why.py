"""A move's why reaches its journal entry, and a cascaded move is projected at
`full` like any other governed move (#1232).

A bypass's justification — `promote-issue --reason`, `move-issue --bypass
--bypass-reason` — was written into the audit comment only, so the journal
lacked the why of exactly the moves that needed one. It is now the move's
journal entry's reason too (`bypass: <reason>`), at every audit projection, and
`pkit pm history` shows it. A move no gate was bypassed for carries none.

At `audit.projection: full` every governed move gets a provenance comment
(DEC-049), and an ancestor the forward cascade moved got none. It now gets one,
naming the move that caused it: one comment on each ancestor per run, covering
the steps that landed in it, so a re-run never repeats one. At `audit` and
`off` a cascaded move posts nothing. A comment that fails to post is one
warning line, and the move stands.

These tests run the real scripts and the real engine against an in-memory GitHub
(`tests/pm_lifecycle_world.py`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from tests.pm_lifecycle_world import (
    AUDIT_MARKER,
    AUTHORED_BODY,
    INVOKER,
    REASON,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    wire,
)

#: The pkit version a provenance comment is stamped with in these tests.
VERSION = "9.9.9"
CONTAINER_BODY = "## What\n\nA container.\n"


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_journal_why")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_journal_why")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_journal_why")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_journal_why")


@pytest.fixture
def engine_repo(tmp_path: Path) -> Path:
    return make_engine_repo(tmp_path)


@pytest.fixture
def world(engine_repo: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), engine_repo, ci, pi, mi, hist)
    wire(world, monkeypatch)
    monkeypatch.setattr(mi, "_pkit_version", lambda: VERSION)
    return world


# --- building a hierarchy and setting the projection -----------------------


def _epic_feature_task(world: World, task_state: str = "") -> tuple[int, int, int]:
    """An EPIC and a Feature under it, both in Todo, and a Task under the
    Feature, in `task_state` when one is given (Todo otherwise)."""
    epic = world.file_issue(body=CONTAINER_BODY, title="[EPIC] An epic", labels=())
    feature = world.file_issue(
        body=f"EPIC: #{epic}\n\n{CONTAINER_BODY}", title="[Feature] A feature", labels=()
    )
    labels = ("type:task", f"state:{task_state}") if task_state else ("type:task",)
    task = world.file_issue(body=f"Feature: #{feature}\n\n{AUTHORED_BODY}", labels=labels)
    return epic, feature, task


def _with_projection(world: World, monkeypatch: pytest.MonkeyPatch, level: str) -> None:
    """Run move-issue under the capability's own configuration with
    `audit.projection` set to `level`."""
    read_yaml = world.mi._read_yaml

    def read(path: Path, loader):
        data = read_yaml(path, loader)
        return {**data, "audit": {"projection": level}} if path.name == "config.yaml" else data

    monkeypatch.setattr(world.mi, "_read_yaml", read)


def _fail_one_edit(world: World, monkeypatch: pytest.MonkeyPatch, number: int, label: str) -> None:
    """Fail the next `gh issue edit` on issue `number` that adds `label`, once."""
    edit = world.tracker._edit
    pending = [True]

    def failing(argv: list[str], n: int) -> subprocess.CompletedProcess[str]:
        if pending and n == number and label in argv:
            pending.clear()
            return subprocess.CompletedProcess(argv, 1, "", "HTTP 502: Bad Gateway")
        return edit(argv, n)

    monkeypatch.setattr(world.tracker, "_edit", failing)


def _comments(world: World, number: int) -> list[str]:
    return [comment["body"] for comment in world.tracker.comments[number]]


def _provenance(moves: str, cause: str | None = None) -> str:
    """The provenance comment a governed move through `moves` gets, naming
    `cause` when another move caused it."""
    actor = INVOKER.github_login
    comment = f"{AUDIT_MARKER}\n{actor} moved {moves} (governed by pkit) — pkit {VERSION}"
    return f"{comment}\n{cause}" if cause else comment


def _cascade(child: int, move: str) -> str:
    return f"forward cascade from #{child}: {move}"


def _reasons(world: World, number: int) -> list[str | None]:
    return [entry.get("reason") for entry in world.journal(number)]


# --- a bypass's justification reaches the journal ---------------------------


def test_a_promotions_reason_is_on_its_journal_entry_and_history_shows_it(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    task = world.file_issue()

    assert world.promote(task) == 0

    assert world.moves(task) == [("todo", "backlog", "promote-issue")]
    assert _reasons(world, task) == [f"bypass: {REASON}"]
    # The audit comment carries the same justification.
    assert len(world.audit_comments(task)) == 1

    capsys.readouterr()
    assert world.history(task) == 0
    assert f"todo → backlog (promote-issue) — bypass: {REASON}" in capsys.readouterr().out


def test_a_bypass_reason_is_on_its_journal_entry_as_the_audit_comment_gives_it(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    task = world.file_issue()

    assert world.move(task, "backlog", "--bypass", "--bypass-reason", "  the user said so  ") == 0

    assert _reasons(world, task) == ["bypass: the user said so"]
    [comment] = _comments(world, task)
    assert "the user said so" in comment

    capsys.readouterr()
    assert world.history(task) == 0
    assert "todo → backlog (promote-issue) — bypass: the user said so" in capsys.readouterr().out


def test_a_move_no_gate_was_bypassed_for_carries_no_reason(world: World) -> None:
    """Confirmed with `--yes`, the Todo → Backlog gate is passed, not bypassed;
    and `--bypass` on a move whose gate cannot be bypassed bypasses nothing."""
    task = world.file_issue()

    assert world.move(task, "backlog") == 0
    assert world.move(task, "in-progress", "--bypass", "--bypass-reason", "not needed") == 0

    assert world.moves(task) == [
        ("todo", "backlog", "promote-issue"),
        ("backlog", "in-progress", "start-work"),
    ]
    assert _reasons(world, task) == [None, None]


def test_with_comments_off_a_bypass_reason_still_reaches_the_journal(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _with_projection(world, monkeypatch, "off")
    task = world.file_issue()

    assert world.promote(task) == 0

    assert _comments(world, task) == []
    assert _reasons(world, task) == [f"bypass: {REASON}"]


# --- a cascaded move at `full` ------------------------------------------------


def test_at_full_each_ancestor_gets_one_comment_naming_the_move_that_caused_it(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Task starts while its Feature and EPIC are in Todo: each ancestor is
    taken through Backlog to In Progress, two governed moves, and gets one
    provenance comment naming both and the Task's start — the reason each move
    is journaled with."""
    _with_projection(world, monkeypatch, "full")
    epic, feature, task = _epic_feature_task(world, task_state="backlog")

    assert world.move(task, "in-progress") == 0

    cause = _cascade(task, "backlog → in-progress")
    for number in (feature, epic):
        assert _comments(world, number) == [_provenance("todo → backlog → in-progress", cause)]
        assert _reasons(world, number) == [cause, cause]
    # The Task's own comment is the one a direct move gets.
    assert _comments(world, task) == [_provenance("backlog → in-progress")]

    # The same move again, and a sibling's moves, find the ancestors level: no
    # ancestor is moved again, so none is commented on again.
    assert world.move(task, "in-progress") == 0
    sibling = world.file_issue(body=f"Feature: #{feature}\n\n{AUTHORED_BODY}")
    assert world.promote(sibling) == 0
    assert world.move(sibling, "in-progress") == 0
    for number in (feature, epic):
        assert _comments(world, number) == [_provenance("todo → backlog → in-progress", cause)]


def test_at_full_a_promotion_audits_the_issue_and_projects_each_ancestor(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The promoted issue gets its one audit comment, which at `full` stands for
    the provenance comment too; each ancestor it brings to Backlog gets a
    provenance comment of its own."""
    _with_projection(world, monkeypatch, "full")
    epic, feature, task = _epic_feature_task(world)

    assert world.promote(task) == 0

    assert len(_comments(world, task)) == 1
    assert len(world.audit_comments(task)) == 1
    cause = _cascade(task, "todo → backlog")
    for number in (feature, epic):
        assert _comments(world, number) == [_provenance("todo → backlog", cause)]


@pytest.mark.parametrize("level", ["audit", "off"])
def test_below_full_a_cascaded_move_posts_nothing(
    world: World, monkeypatch: pytest.MonkeyPatch, level: str
) -> None:
    _with_projection(world, monkeypatch, level)
    epic, feature, task = _epic_feature_task(world)

    assert world.promote(task) == 0
    assert world.move(task, "in-progress") == 0

    for number in (feature, epic):
        assert _comments(world, number) == []
        assert world.views(number) == ("in-progress", "in-progress")
        assert len(world.journal(number)) == 2


def test_a_comment_that_fails_to_post_is_one_warning_and_the_move_stands(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _with_projection(world, monkeypatch, "full")
    epic, feature, task = _epic_feature_task(world, task_state="backlog")
    world.tracker.comments_fail.add(feature)
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    out, err = capsys.readouterr()
    assert err == (
        f"  [warn] #{feature}: its provenance comment was not posted (gh issue comment "
        "exited 1: HTTP 502: Bad Gateway); the move stands.\n"
    )
    # The cascade completed: the Feature moved and is journaled, the EPIC above
    # it was moved and commented on.
    assert f"[cascade] forward cascade from #{task}:\n" in out
    assert world.views(feature) == ("in-progress", "in-progress")
    assert len(world.journal(feature)) == 2
    assert _comments(world, feature) == []
    assert _comments(world, epic) == [
        _provenance("todo → backlog → in-progress", _cascade(task, "backlog → in-progress"))
    ]


def test_each_step_that_lands_is_in_exactly_one_comment(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Feature's second step fails: its comment names the step that landed,
    and the run that finishes the cascade comments on the step it makes."""
    _with_projection(world, monkeypatch, "full")
    _epic, feature, task = _epic_feature_task(world, task_state="backlog")
    _fail_one_edit(world, monkeypatch, feature, "state:in-progress")

    assert world.move(task, "in-progress") == 0
    assert _comments(world, feature) == [
        _provenance("todo → backlog", _cascade(task, "backlog → in-progress"))
    ]

    assert world.move(task, "in-progress") == 0
    assert _comments(world, feature) == [
        _provenance("todo → backlog", _cascade(task, "backlog → in-progress")),
        _provenance("backlog → in-progress", _cascade(task, "at in-progress")),
    ]
    assert world.moves(feature) == [
        ("todo", "backlog", "promote-issue"),
        ("backlog", "in-progress", "start-work"),
    ]
