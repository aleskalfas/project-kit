"""The issue a landing completes journals its close with the reason the other
issues its pull request closes get (#1296).

After the merge `done-work` moves its own issue to Done through `move-issue`,
then runs close-issue's pr-merge close on every issue the pull request closed.
GitHub has closed them by then, so the move to Done only rewrites the issue's
stale label, and close-issue then finds that label at Done and records nothing:
the landing's own issue was journaled with no reason, while every other issue
the pull request closed got `pr-merge close: closed by merged PR #<PR>`.
done-work now names the merged pull request to `move-issue` (`--merged-pr`),
and the one entry its move writes carries that same reason. `land-work` lands
through the same two paths: the merge it makes, and the completion of a pull
request already merged.

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
from ruamel.yaml import YAML

from tests.pm_lifecycle_world import (
    CAPABILITY_ROOT,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    wire,
)
from tests.process_journal_support import set_journal_logging

ENGINE_WARNING = "the process engine refused this move"
PR = 500
CLOSED_BY = f"pr-merge close: closed by merged PR #{PR}"
COMPLETED_BY = f"pr-merge close: completed by merged PR #{PR}"


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_done_work_journal")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_done_work_journal")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_done_work_journal")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_done_work_journal")


@pytest.fixture(scope="module")
def cl() -> ModuleType:
    return load_script("close-issue.py", "pm_close_issue_done_work_journal")


@pytest.fixture(scope="module")
def dw() -> ModuleType:
    return load_script("done-work.py", "pm_done_work_done_work_journal")


@pytest.fixture
def world(tmp_path: Path, ci, pi, mi, hist, cl, dw, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), make_engine_repo(tmp_path), ci, pi, mi, hist, cl)
    wire(world, monkeypatch)
    # The branch clean-up after the closes is another test's subject.
    monkeypatch.setattr(dw.pr_merge, "delete_branch", lambda *a, **kw: None)
    monkeypatch.setattr(dw.pr_merge, "cleanup_local", lambda *a, **kw: None)
    return world


# --- the issues a pull request closes -----------------------------------------


def _backlog_task(world: World) -> int:
    number = world.file_issue()
    assert world.promote(number) == 0
    return number


def _task_in_review(world: World) -> int:
    number = _backlog_task(world)
    assert world.move(number, "in-progress") == 0
    assert world.move(number, "review") == 0
    return number


def _landing(world: World) -> tuple[int, int]:
    """A pull request that closes its own issue, in Review, and one other, in
    Backlog, merged: GitHub closed both and left their labels in place."""
    primary, further = _task_in_review(world), _backlog_task(world)
    world.tracker.merge(PR, [primary, further])
    return primary, further


def _landing_github_left_open(world: World) -> tuple[int, int]:
    """The same pull request merged into a base GitHub does not close issues on:
    both are still open after the merge."""
    primary, further = _landing(world)
    for number in (primary, further):
        world.tracker.issues[number].update(state="OPEN", state_reason=None)
    return primary, further


# --- the two ways a landing completes -----------------------------------------


def _args(primary: int) -> argparse.Namespace:
    return argparse.Namespace(
        issue_number=primary,
        capability_root=CAPABILITY_ROOT,
        skip_checkbox_gate=False,
        dry_run=False,
        yes=True,
    )


def _after_the_merge(world: World, dw: ModuleType, primary: int, further: int) -> int:
    """What done-work runs once the merge it made has landed."""
    run = dw._after_merge(
        _args(primary),
        pr_number=PR,
        to_close=[primary, further],
        branch=f"fix/{primary}-a-task",
        cross=False,
        merged_head="0" * 40,
        config={},
        confirmed=False,
    )
    return int(run.exit_code)


def _completing_the_merged_pr(world: World, dw: ModuleType, primary: int, further: int) -> int:
    """What done-work runs on a pull request already merged — a merge queue's,
    say — which reads the issues it closes from the pull request's body."""
    merged = {
        **world.tracker.merged_prs[PR],
        "headRefName": f"fix/{primary}-a-task",
        "headRefOid": "0" * 40,
        "isCrossRepository": False,
    }
    run = dw._complete_merged_pr(
        _args(primary),
        merged,
        dw._IssueMerges([]),
        capability_root=CAPABILITY_ROOT,
        yaml_loader=YAML(typ="safe"),
        config={},
        confirmed=False,
    )
    return int(run.exit_code)


LANDINGS = [
    pytest.param(_after_the_merge, id="after-the-merge"),
    pytest.param(_completing_the_merged_pr, id="already-merged"),
]
Land = Callable[[World, ModuleType, int, int], int]


def _engine_calls_during(world: World, step: Callable[[], Any]) -> tuple[Any, list[list[str]]]:
    """Run `step`; return what it returned and the `pkit process` calls it made."""
    before = len(world.engine_calls)
    result = step()
    return result, world.engine_calls[before:]


# --- the move to Done carries the reason --------------------------------------


@pytest.mark.parametrize("land", LANDINGS)
def test_the_landings_own_issue_is_journaled_with_the_reason_the_other_gets(
    world: World, dw: ModuleType, capsys: pytest.CaptureFixture[str], land: Land
) -> None:
    primary, further = _landing(world)
    capsys.readouterr()

    assert land(world, dw, primary, further) == 0

    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.moves(primary)[-1] == ("review", "done", "done-work")
    assert world.moves(further)[-1] == ("backlog", "done", "close-issue")
    for number in (primary, further):
        assert world.views(number) == ("done", "done")
        # One entry for the move to Done, carrying the merge's reason.
        [entry] = [entry for entry in world.journal(number) if entry["to"] == "done"]
        assert entry["reason"] == CLOSED_BY
        assert world.history(number) == 0
        history = capsys.readouterr().out
        assert f"→ done ({entry['trigger']}) — {CLOSED_BY}" in history
        assert "no ungoverned state changes detected" in history


@pytest.mark.parametrize("land", LANDINGS)
def test_landing_again_records_nothing_more(
    world: World, dw: ModuleType, capsys: pytest.CaptureFixture[str], land: Land
) -> None:
    primary, further = _landing(world)
    assert land(world, dw, primary, further) == 0
    journals = {number: world.journal(number) for number in (primary, further)}

    assert land(world, dw, primary, further) == 0

    assert {number: world.journal(number) for number in (primary, further)} == journals


def test_an_issue_the_merge_left_open_is_journaled_as_completed_by_the_pr(
    world: World, dw: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    """On a base GitHub does not close issues on, done-work's move to Done is the
    move Review → Done itself, and close-issue then closes each issue through
    the pull request: both entries read as close-issue words that close."""
    primary, further = _landing_github_left_open(world)
    capsys.readouterr()

    assert _after_the_merge(world, dw, primary, further) == 0

    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.moves(primary)[-1] == ("review", "done", "done-work")
    assert world.moves(further)[-1] == ("backlog", "done", "close-issue")
    for number in (primary, further):
        assert world.tracker.issues[number]["state"] == "CLOSED"
        [entry] = [entry for entry in world.journal(number) if entry["to"] == "done"]
        assert entry["reason"] == COMPLETED_BY
        assert world.history(number) == 0


# --- journal logging off ------------------------------------------------------


@pytest.mark.parametrize("land", LANDINGS)
def test_with_journal_logging_off_a_landing_records_nothing(
    world: World, dw: ModuleType, capsys: pytest.CaptureFixture[str], land: Land
) -> None:
    set_journal_logging(world.engine_repo, enabled=False)
    primary, further = _landing(world)

    rc, calls = _engine_calls_during(world, lambda: land(world, dw, primary, further))

    assert rc == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.journal_files() == []
    for number in (primary, further):
        assert world.views(number) == ("done", "done")
    # The engine says no journal is kept, so the relabel of the landing's own
    # issue is not handed to it; close-issue asks it once for the other issue's
    # close, as it asks for every close, and nothing is recorded.
    moves = [call for call in calls if call[2] == "move"]
    assert [call[call.index("--subject") + 1] for call in moves] == [str(further)]


# --- the flag ---------------------------------------------------------------


def test_merged_pr_is_refused_on_a_move_to_any_state_but_done(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    number = _backlog_task(world)
    world.tracker.calls.clear()
    capsys.readouterr()

    assert world.move(number, "in-progress", "--merged-pr", str(PR)) == 2

    assert (
        "error: --merged-pr applies to --to done only (got --to in-progress)."
        in capsys.readouterr().err
    )
    assert world.tracker.calls == []
    assert world.views(number) == ("backlog", "backlog")
