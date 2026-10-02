"""Each close `close-issue` makes is journaled, from where the issue was (#1231).

A won't-do close, a cascade-eligible container's close, and a pr-merge close —
the one `done-work` runs on each issue a merged pull request closes — wrote the
Done label and recorded nothing with the process engine. With journal logging
on, `pkit pm history <N> --check-drift` then reported drift for a close pkit
made, and the audit trail had a hole at the end of every issue's life
([project-management:DEC-049-audit-journal-model]). Each close now records one
move to Done through the path `move-issue` records its moves through
(`pkit process move --from`): from the state the issue held before the close,
with the close mode as the entry's reason.

These tests run the real scripts and the real engine against an in-memory GitHub
(`tests/pm_lifecycle_world.py`).
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.pm_lifecycle_world import (
    AUTHORED_BODY,
    CAPABILITY_ROOT,
    INVOKER,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    wire,
)
from tests.process_journal_support import set_journal_logging

ENGINE_WARNING = "the process engine refused this move"
WONT_DO_REASON = "superseded by #99"
PR = 500

UNTICKED_BODY = AUTHORED_BODY.replace("- [x]", "- [ ]")


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_close_journal")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_close_journal")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_close_journal")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_close_journal")


@pytest.fixture(scope="module")
def cl() -> ModuleType:
    return load_script("close-issue.py", "pm_close_issue_close_journal")


@pytest.fixture(scope="module")
def dw() -> ModuleType:
    return load_script("done-work.py", "pm_done_work_close_journal")


@pytest.fixture
def engine_repo(tmp_path: Path) -> Path:
    return make_engine_repo(tmp_path)


@pytest.fixture
def world(engine_repo: Path, ci, pi, mi, hist, cl, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), engine_repo, ci, pi, mi, hist, cl)
    wire(world, monkeypatch)
    # A container's close reads the engine's fold over its children first — an
    # engine call of that mode's own, answered by predicates this harness does
    # not run. Every child has closed, it says here.
    monkeypatch.setattr(cl, "_engine_cascade_fold", lambda _n: {"opened": True})
    return world


def _engine_calls_during(world: World, step: Callable[[], Any]) -> tuple[Any, list[list[str]]]:
    """Run `step`; return what it returned and the `pkit process` calls it made."""
    before = len(world.engine_calls)
    result = step()
    return result, world.engine_calls[before:]


# --- the issues closed --------------------------------------------------------


def _backlog_task(world: World, body: str = AUTHORED_BODY) -> int:
    number = world.file_issue(body=body)
    assert world.promote(number) == 0
    return number


def _task_in_review(world: World) -> int:
    number = _backlog_task(world)
    assert world.move(number, "in-progress") == 0
    assert world.move(number, "review") == 0
    return number


def _container_in_progress(world: World) -> int:
    """A Feature its child's start has cascaded to In Progress."""
    parent = world.file_issue(title="[Feature] A feature", labels=())
    child = world.file_issue(body=f"Feature: #{parent}\n\n{AUTHORED_BODY}")
    assert world.promote(child) == 0
    assert world.move(child, "in-progress") == 0
    return parent


def _merged_task_in_review(world: World) -> int:
    """What done-work's pr-merge close finds: GitHub closed the issue as the
    pull request merged and left its Review label in place."""
    number = _task_in_review(world)
    world.tracker.merge(PR, [number])
    return number


#: (the issue's set-up, the close, the move it records, the trigger the workflow
#: names that move by, the reason recorded on it)
CLOSES = [
    pytest.param(
        _backlog_task,
        ["--reason", WONT_DO_REASON],
        ("backlog", "done"),
        "close-issue",
        f"wont-do close: {WONT_DO_REASON}",
        id="wont-do",
    ),
    pytest.param(
        _container_in_progress,
        ["--mode", "cascade-eligibility-close"],
        ("in-progress", "done"),
        "close-issue",
        "cascade-eligibility close: every child closed and every checkbox ticked",
        id="cascade-eligibility-close",
    ),
    pytest.param(
        _merged_task_in_review,
        ["--mode", "pr-merge", "--pr", str(PR)],
        ("review", "done"),
        "done-work",
        f"pr-merge close: closed by merged PR #{PR}",
        id="pr-merge",
    ),
]
CLOSE_FIELDS = ("set_up", "options", "move", "trigger", "reason")


# --- each close is journaled once ---------------------------------------------


@pytest.mark.parametrize(CLOSE_FIELDS, CLOSES)
def test_each_close_journals_one_move_from_where_the_issue_was(
    world: World,
    capsys: pytest.CaptureFixture[str],
    set_up: Callable[[World], int],
    options: list[str],
    move: tuple[str, str],
    trigger: str,
    reason: str,
) -> None:
    number = set_up(world)
    before = world.journal(number)

    rc, calls = _engine_calls_during(world, lambda: world.close(number, *options))

    assert rc == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.views(number) == ("done", "done")
    journal = world.journal(number)
    assert journal[: len(before)] == before
    [entry] = journal[len(before) :]
    assert (entry["from"], entry["to"], entry["trigger"]) == (*move, trigger)
    assert entry["reason"] == reason
    assert entry["actor"] == INVOKER.github_login
    # One engine call records the close, and nothing reads the engine before it.
    assert [call[2] for call in calls] == ["move"]


@pytest.mark.parametrize(CLOSE_FIELDS, CLOSES)
def test_check_drift_finds_no_drift_after_each_close(
    world: World,
    capsys: pytest.CaptureFixture[str],
    set_up: Callable[[World], int],
    options: list[str],
    move: tuple[str, str],
    trigger: str,
    reason: str,
) -> None:
    number = set_up(world)
    assert world.close(number, *options) == 0
    capsys.readouterr()

    assert world.history(number) == 0
    history = capsys.readouterr().out
    assert f"{move[0]} → done ({trigger}) — {reason}" in history
    assert "no ungoverned state changes detected" in history


@pytest.mark.parametrize(CLOSE_FIELDS, CLOSES)
def test_a_rerun_records_nothing_more(
    world: World,
    set_up: Callable[[World], int],
    options: list[str],
    move: tuple[str, str],
    trigger: str,
    reason: str,
) -> None:
    number = set_up(world)
    assert world.close(number, *options) == 0
    journaled = world.journal(number)

    # Won't-do and the container's close find the issue closed; pr-merge finds
    # its label at done.
    rc, calls = _engine_calls_during(world, lambda: world.close(number, *options))

    assert rc == 0
    assert calls == []
    assert world.journal(number) == journaled
    assert world.history(number) == 0


def test_a_close_through_a_pr_that_did_not_name_the_issue_is_journaled(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--pr` closes an open leaf whose work landed in a pull request that
    closed another issue; the close is recorded from where the leaf was."""
    landed_elsewhere = _backlog_task(world)
    world.tracker.merge(PR, [_task_in_review(world)])
    capsys.readouterr()

    assert world.close(landed_elsewhere, "--mode", "pr-merge", "--pr", str(PR)) == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.moves(landed_elsewhere)[-1] == ("backlog", "done", "close-issue")
    assert world.journal(landed_elsewhere)[-1]["reason"] == (
        f"pr-merge close: completed by merged PR #{PR}"
    )
    assert world.history(landed_elsewhere) == 0


# --- a close that is not recorded ---------------------------------------------


def test_a_close_the_engine_refuses_is_reported_like_a_direct_moves_refusal(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    # Backlog → Done is gated on every checkbox being ticked. The close skips
    # its own checkbox gate and goes ahead; the engine refuses to record it.
    number = _backlog_task(world, body=UNTICKED_BODY)
    capsys.readouterr()

    rc, calls = _engine_calls_during(
        world,
        lambda: world.close(number, "--reason", WONT_DO_REASON, "--skip-checkbox-gate"),
    )

    closed = capsys.readouterr()
    assert rc == 0
    assert [call[2] for call in calls] == ["move"]
    assert (
        f"[warn] {ENGINE_WARNING}: refused: gate refused: 1 unticked checkbox(es) remain. "
        in closed.err
    )
    assert f"`pkit pm history {number} --check-drift` will show the gap" in closed.err
    # The close stands; what is left is a closed issue the journal has no entry
    # for, which the drift check shows.
    assert f"[ok] closed #{number} (wont-do)." in closed.out
    assert world.views(number) == ("done", "done")
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]
    assert world.history(number) == 3


def test_a_close_the_workflow_does_not_declare_for_the_type_is_not_recorded(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    # The workflow declares In Progress → Done for containers only. The engine
    # does not read a transition's `applies_to`, so it would record the move
    # for a Task; close-issue does not hand it over, and says so.
    number = _backlog_task(world)
    assert world.move(number, "in-progress") == 0
    capsys.readouterr()

    rc, calls = _engine_calls_during(world, lambda: world.close(number, "--reason", WONT_DO_REASON))

    closed = capsys.readouterr()
    assert rc == 0
    assert calls == []
    assert (
        "[warn] this move was not recorded: no transition 'in-progress' → 'done' "
        "declared in workflow.yaml for 'task'. "
    ) in closed.err
    assert f"`pkit pm history {number} --check-drift` will show the gap" in closed.err
    assert f"[ok] closed #{number} (wont-do)." in closed.out
    assert world.views(number) == ("done", "done")
    assert world.moves(number) == [
        ("todo", "backlog", "promote-issue"),
        ("backlog", "in-progress", "start-work"),
    ]
    assert world.history(number) == 3


# --- journal logging off ------------------------------------------------------


@pytest.mark.parametrize(CLOSE_FIELDS, CLOSES)
def test_with_journal_logging_off_nothing_is_journaled(
    world: World,
    capsys: pytest.CaptureFixture[str],
    set_up: Callable[[World], int],
    options: list[str],
    move: tuple[str, str],
    trigger: str,
    reason: str,
) -> None:
    set_journal_logging(world.engine_repo, enabled=False)
    number = set_up(world)

    rc, calls = _engine_calls_during(world, lambda: world.close(number, *options))

    assert rc == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.views(number) == ("done", "done")
    assert world.journal_files() == []
    # Whether a move is recorded is the engine's to say: the close asks it once,
    # as move-issue asks for each move, and it records nothing. Nothing else is
    # asked of it.
    assert [call[2] for call in calls] == ["move"]


# --- move-issue on an issue GitHub closed -------------------------------------
#
# A closed issue reads as done, so `move-issue --to done` on one GitHub closed
# finds it there and only rewrites its stale label — the move done-work makes on
# its own issue after a merge. That label write is recorded, once.


def test_relabelling_an_issue_github_closed_journals_the_close_once(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    number = _merged_task_in_review(world)
    capsys.readouterr()

    assert world.move(number, "done") == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert "state:done" in world.labels(number)
    assert world.moves(number)[-1] == ("review", "done", "done-work")
    assert world.history(number) == 0

    journaled = world.journal(number)
    rc, calls = _engine_calls_during(world, lambda: world.move(number, "done"))
    assert rc == 0
    assert [call[2] for call in calls] == ["status"]
    assert world.journal(number) == journaled


def test_with_journal_logging_off_relabelling_a_closed_issue_asks_the_engine_nothing_more(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    set_journal_logging(world.engine_repo, enabled=False)
    number = _merged_task_in_review(world)

    rc, calls = _engine_calls_during(world, lambda: world.move(number, "done"))

    assert rc == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert "state:done" in world.labels(number)
    assert world.journal_files() == []
    # The status read it makes anyway says no journal is kept.
    assert [call[2] for call in calls] == ["status"]


# --- a done-work landing ------------------------------------------------------


def test_a_done_work_landing_that_closes_two_issues_journals_each_once(
    world: World,
    dw: ModuleType,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After the merge done-work moves its issue to Done through move-issue,
    then runs close-issue's pr-merge close on every issue the pull request
    closed, its own first. GitHub closed both as the pull request merged."""
    primary = _task_in_review(world)
    further = _backlog_task(world)
    world.tracker.merge(PR, [primary, further])
    monkeypatch.setattr(dw.pr_merge, "delete_remote_branch", lambda *a, **kw: None)
    monkeypatch.setattr(dw.pr_merge, "cleanup_local", lambda *a, **kw: None)
    capsys.readouterr()

    def land() -> int:
        run = dw._after_merge(
            argparse.Namespace(
                issue_number=primary,
                capability_root=CAPABILITY_ROOT,
                skip_checkbox_gate=False,
            ),
            pr_number=PR,
            to_close=[primary, further],
            branch=f"fix/{primary}-a-task",
            cross=False,
            merged_head="0" * 40,
            config={},
            confirmed=False,
        )
        return int(run.exit_code)

    assert land() == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.moves(primary)[-1] == ("review", "done", "done-work")
    assert world.moves(further)[-1] == ("backlog", "done", "close-issue")
    for number in (primary, further):
        assert world.views(number) == ("done", "done")
        assert [to for _from, to, _trigger in world.moves(number)].count("done") == 1
        assert world.history(number) == 0
        assert "no ungoverned state changes detected" in capsys.readouterr().out

    # Landing again records nothing more.
    journals = {number: world.journal(number) for number in (primary, further)}
    assert land() == 0
    assert {number: world.journal(number) for number in (primary, further)} == journals
