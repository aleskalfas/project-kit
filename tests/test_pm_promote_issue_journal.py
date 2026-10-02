"""Promoting a freshly filed issue records one move, Todo → Backlog (#1183).

`move-issue` writes the state label first and asks the process engine to record
the move second, in the order the process README's seam-ordering contract sets.
By then live detection reads the label just written. The engine took the live
position for the move's origin, so `promote-issue` had it asked for backlog →
backlog; it refused, and every successful promotion printed "the process engine
refused this move". `move-issue` now names the origin it read before the label
write (`pkit process move --from`).

Promoting with `--milestone` made no move at all (#1210). promote-issue attached
the milestone first, and the workflow reads a milestone as Backlog, so its
move-issue found nothing to move: no state label, no audit comment, nothing
journaled. It now moves first and attaches the milestone second, and a re-run
after a failure between the two completes the promotion without a second audit
comment.

These tests run the sequence through the real scripts and the real engine. The
issue is filed with create-issue's own tracker call, then promoted by
promote-issue, whose move-issue runs in this process. GitHub is an in-memory
tracker. The engine runs the shipped issue-lifecycle definition in a scratch
repository, and its predicates answer from that tracker through the capability's
own predicate code. After each step the tracker's view of the issue's state and
the engine's are compared.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from tests.pm_lifecycle_world import (
    AUTHORED_BODY,
    MILESTONE,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    wire,
)
from tests.process_journal_support import set_journal_logging

ENGINE_WARNING = "the process engine refused this move"

UNTICKED_BODY = AUTHORED_BODY.replace("- [x]", "- [ ]")


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_journal_sequence")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_journal_sequence")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_journal_sequence")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_journal_sequence")


@pytest.fixture
def engine_repo(tmp_path: Path) -> Path:
    return make_engine_repo(tmp_path)


@pytest.fixture
def world(engine_repo: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), engine_repo, ci, pi, mi, hist)
    wire(world, monkeypatch)
    return world


# --- the sequence ---------------------------------------------------------


def test_promoting_a_filed_issue_journals_one_todo_to_backlog_move(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    number = world.file_issue()
    assert world.views(number) == ("todo", "todo")
    assert world.moves(number) == []

    assert world.promote(number) == 0
    promoted = capsys.readouterr()
    assert ENGINE_WARNING not in promoted.err
    assert f"[ok] promoted #{number} Todo → Backlog" in promoted.out
    assert world.views(number) == ("backlog", "backlog")
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]

    # `pkit pm history` shows the one move, and the timeline holds no state
    # change the journal lacks.
    assert world.history(number) == 0
    history = capsys.readouterr().out
    assert history.count("todo → backlog (promote-issue)") == 1
    assert "no ungoverned state changes detected" in history


def test_with_journal_logging_off_promoting_prints_no_engine_warning(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    set_journal_logging(world.engine_repo, enabled=False)
    number = world.file_issue()
    assert world.views(number) == ("todo", "todo")

    assert world.promote(number) == 0
    promoted = capsys.readouterr()
    assert ENGINE_WARNING not in promoted.err
    assert f"[ok] promoted #{number} Todo → Backlog" in promoted.out
    assert world.views(number) == ("backlog", "backlog")
    assert world.journal_files() == []


def test_the_next_move_journals_its_own_transition_not_a_self_loop(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    # In Progress declares a move to itself (create-draft). Taking the live
    # position for the origin journaled Backlog → In Progress as that self-loop,
    # silently, where Todo → Backlog was refused out loud.
    number = world.file_issue()
    assert world.promote(number) == 0

    assert world.move(number, "in-progress") == 0
    assert ENGINE_WARNING not in capsys.readouterr().err
    assert world.views(number) == ("in-progress", "in-progress")
    assert world.moves(number) == [
        ("todo", "backlog", "promote-issue"),
        ("backlog", "in-progress", "start-work"),
    ]


def test_a_move_the_engine_refuses_still_warns(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    # Backlog → Done is gated on every checkbox being ticked. move-issue writes
    # the label regardless, and the engine refuses to record the move.
    number = world.file_issue(body=UNTICKED_BODY)
    assert world.promote(number) == 0
    capsys.readouterr()

    assert world.move(number, "done") == 0
    moved = capsys.readouterr()
    assert world.views(number) == ("done", "done")
    assert (
        f"[warn] {ENGINE_WARNING}: refused: gate refused: 1 unticked checkbox(es) remain. "
        in moved.err
    )
    assert f"`pkit pm history {number} --check-drift` will show the gap" in moved.err
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]


# --- scheduling while promoting (#1210) -------------------------------------


def _assert_promoted(world: World, number: int, milestone: str | None) -> None:
    """The issue is in Backlog on both views with `milestone` set (or none), one
    audit comment carries the reason, and the journal holds one todo → backlog
    move that `pm history --check-drift` finds no drift against."""
    assert world.views(number) == ("backlog", "backlog")
    assert "state:backlog" in world.labels(number)
    assert world.milestone(number) == milestone
    assert len(world.audit_comments(number)) == 1
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]
    assert world.history(number) == 0


def test_promoting_with_a_milestone_makes_the_whole_move_and_schedules(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    # Attached first, the milestone read as Backlog: move-issue found nothing
    # to move, and the issue ended with the milestone and nothing else.
    number = world.file_issue()
    assert world.views(number) == ("todo", "todo")

    assert world.promote(number, milestone=MILESTONE["title"]) == 0
    promoted = capsys.readouterr()
    assert ENGINE_WARNING not in promoted.err
    assert f"[ok] promoted #{number} Todo → Backlog (milestone: Sprint 1)" in promoted.out
    _assert_promoted(world, number, milestone="Sprint 1")
    assert "no ungoverned state changes detected" in capsys.readouterr().out


def test_a_rerun_after_the_milestone_write_fails_attaches_it_without_moving_again(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    number = world.file_issue()
    world.tracker.fail_next = {"--milestone"}

    assert world.promote(number, milestone=MILESTONE["title"]) == 2
    assert (
        f"[warn] #{number} was moved to Backlog but milestone 'Sprint 1' was not attached."
        in capsys.readouterr().err
    )
    # The move is whole; only the milestone is missing.
    assert "state:backlog" in world.labels(number)
    assert world.milestone(number) is None
    assert len(world.audit_comments(number)) == 1
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]

    assert world.promote(number, milestone=MILESTONE["title"]) == 0
    assert f"[ok] #{number} already at state:backlog (milestone attached" in (
        capsys.readouterr().out
    )
    _assert_promoted(world, number, milestone="Sprint 1")


def test_a_rerun_after_the_label_write_fails_posts_the_audit_comment_once(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    # move-issue posts the audit comment before the label write, so the reason
    # survives the failure; the re-run finds that comment by its key and moves.
    number = world.file_issue()
    world.tracker.fail_next = {"--add-label"}

    assert world.promote(number, milestone=MILESTONE["title"]) == 3
    assert (
        f"[warn] move-issue exited 3: #{number} was not moved and milestone 'Sprint 1' "
        "was not attached" in capsys.readouterr().err
    )
    assert world.views(number) == ("todo", "todo")
    assert world.milestone(number) is None
    assert len(world.audit_comments(number)) == 1
    assert world.moves(number) == []

    assert world.promote(number, milestone=MILESTONE["title"]) == 0
    assert "transition audit comment already present" in capsys.readouterr().out
    _assert_promoted(world, number, milestone="Sprint 1")


def test_promoting_without_a_milestone_leaves_the_milestone_alone(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    number = world.file_issue()

    assert world.promote(number) == 0
    assert f"[ok] promoted #{number} Todo → Backlog (milestone unchanged)" in (
        capsys.readouterr().out
    )
    _assert_promoted(world, number, milestone=None)
    assert world.milestone_calls() == []
