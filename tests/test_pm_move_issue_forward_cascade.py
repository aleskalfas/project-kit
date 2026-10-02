"""The forward cascade brings every ancestor of a moved issue level (#1230).

When an issue moves forward, `move-issue` walks from it to the top of its
hierarchy — its parent, that parent's parent, and so on — and brings each
ancestor that is behind up to the issue's state, capped at In Progress
(DEC-006). It reads each ancestor once, before it writes anything, and prints
the walk as the preview; it asks the engine where an ancestor is only when it
is about to move it. An ancestor at or past the target is left alone and the
walk goes on above it. The walk stops at an ancestor it cannot read, one that
is not a container, one it has passed already, and one whose native parent is
not the parent its first line names. The cascade ends with one block saying
what became of each ancestor, and the issue's own move stands whatever the
cascade did.

These tests run the real scripts and the real engine against an in-memory GitHub
(`tests/pm_lifecycle_world.py`).
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from tests.pm_lifecycle_world import (
    AUTHORED_BODY,
    INVOKER,
    MILESTONE,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    wire,
)
from tests.process_journal_support import set_journal_logging

ENGINE_WARNING = "the process engine refused this move"
CONTAINER_BODY = "## What\n\nA container.\n"


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_forward_cascade")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_forward_cascade")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_forward_cascade")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_forward_cascade")


@pytest.fixture
def engine_repo(tmp_path: Path) -> Path:
    return make_engine_repo(tmp_path)


@pytest.fixture
def world(engine_repo: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), engine_repo, ci, pi, mi, hist)
    wire(world, monkeypatch)
    return world


# --- building a hierarchy --------------------------------------------------


def _container(
    world: World, title: str, parent: int | None = None, ref: str = "EPIC", state: str = ""
) -> int:
    """File a container, under `parent` (named by `ref`) when one is given, in
    `state` (a state label) when one is given."""
    body = f"{ref}: #{parent}\n\n{CONTAINER_BODY}" if parent else CONTAINER_BODY
    return world.file_issue(body=body, title=title, labels=(f"state:{state}",) if state else ())


def _task(world: World, parent: int, ref: str = "Feature", state: str = "") -> int:
    labels = ("type:task", f"state:{state}") if state else ("type:task",)
    return world.file_issue(body=f"{ref}: #{parent}\n\n{AUTHORED_BODY}", labels=labels)


def _epic_feature_task(world: World, **states: str) -> tuple[int, int, int]:
    """An EPIC, a Feature under it and a Task under that, each in the state
    `states` gives it (Todo by default)."""
    epic = _container(world, "[EPIC] An epic", state=states.get("epic", ""))
    feature = _container(
        world, "[Feature] A feature", epic, "EPIC", state=states.get("feature", "")
    )
    task = _task(world, feature, state=states.get("task", ""))
    return epic, feature, task


def _reason(child: int, move: str) -> str:
    return f"forward cascade from #{child}: {move}"


def _no_drift(world: World, capsys: pytest.CaptureFixture[str], *numbers: int) -> None:
    for number in numbers:
        capsys.readouterr()
        assert world.history(number) == 0, number
        assert "no ungoverned state changes detected" in capsys.readouterr().out


def _ancestor_engine_calls(world: World, *numbers: int) -> list[list[str]]:
    subjects = {str(n) for n in numbers}
    return [argv for argv in world.engine_calls if argv[argv.index("--subject") + 1] in subjects]


# --- every ancestor, to the top -------------------------------------------


def test_a_tasks_moves_bring_its_feature_and_its_epic_level(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world)

    assert world.promote(task) == 0
    assert world.views(feature) == ("backlog", "backlog")
    assert world.views(epic) == ("backlog", "backlog")

    assert world.move(task, "in-progress") == 0
    out, err = capsys.readouterr()
    assert ENGINE_WARNING not in err
    assert world.views(feature) == ("in-progress", "in-progress")
    assert world.views(epic) == ("in-progress", "in-progress")

    # One entry per step, each naming the task's move that caused it.
    for number in (feature, epic):
        assert world.moves(number) == [
            ("todo", "backlog", "promote-issue"),
            ("backlog", "in-progress", "start-work"),
        ]
        assert [entry["reason"] for entry in world.journal(number)] == [
            _reason(task, "todo → backlog"),
            _reason(task, "backlog → in-progress"),
        ]
        assert {entry["actor"] for entry in world.journal(number)} == {INVOKER.github_login}
    # The closing block lists each ancestor, lowest first.
    assert (
        f"[cascade] forward cascade from #{task}:\n"
        f"  #{feature}: backlog → in-progress\n"
        f"  #{epic}: backlog → in-progress\n"
    ) in out
    _no_drift(world, capsys, feature, epic)


def test_an_umbrella_between_the_task_and_its_epic_is_moved_too(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic = _container(world, "[EPIC] An epic")
    outer = _container(world, "[Umbrella] Outer", epic, "EPIC")
    inner = _container(world, "[Umbrella] Inner", outer, "Umbrella")
    task = _task(world, inner, "Umbrella")

    assert world.promote(task) == 0
    assert world.move(task, "in-progress") == 0

    assert ENGINE_WARNING not in capsys.readouterr().err
    for number in (inner, outer, epic):
        assert world.views(number) == ("in-progress", "in-progress")
        assert world.moves(number) == [
            ("todo", "backlog", "promote-issue"),
            ("backlog", "in-progress", "start-work"),
        ]
    _no_drift(world, capsys, inner, outer, epic)


def test_an_ancestor_at_the_target_is_left_alone_and_the_walk_goes_on(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """An EPIC a one-level cascade left behind its Feature is brought level by
    the next move under it."""
    epic, feature, task = _epic_feature_task(
        world, epic="backlog", feature="in-progress", task="backlog"
    )
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    out = capsys.readouterr().out
    assert f"  #{feature} (feature): in-progress; left alone\n" in out
    assert f"  #{epic} (epic): backlog → in-progress\n" in out
    assert world.moves(feature) == []
    assert world.moves(epic) == [("backlog", "in-progress", "start-work")]
    assert world.views(epic) == ("in-progress", "in-progress")


def test_a_closed_ancestor_is_left_alone_and_the_walk_goes_on(world: World) -> None:
    epic, feature, task = _epic_feature_task(world)
    world.tracker.issues[feature]["state"] = "CLOSED"

    assert world.promote(task) == 0

    assert world.moves(feature) == []
    assert world.labels(feature) == []
    assert world.moves(epic) == [("todo", "backlog", "promote-issue")]


def test_running_the_move_again_brings_an_ancestor_left_behind_level(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """The issue already being in place does not end the walk."""
    epic, feature, task = _epic_feature_task(
        world, epic="backlog", feature="in-progress", task="in-progress"
    )
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    out = capsys.readouterr().out
    assert "[noop] already at target state" in out
    assert world.moves(feature) == []
    assert world.moves(epic) == [("backlog", "in-progress", "start-work")]
    assert world.journal(epic)[0]["reason"] == _reason(task, "at in-progress")
    assert world.moves(task) == []


def test_a_rerun_or_a_siblings_moves_add_nothing(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world)
    assert world.promote(task) == 0
    assert world.move(task, "in-progress") == 0
    journals = {n: world.journal(n) for n in (feature, epic)}

    assert world.move(task, "in-progress") == 0
    sibling = _task(world, feature)
    assert world.promote(sibling) == 0
    assert world.move(sibling, "in-progress") == 0

    assert ENGINE_WARNING not in capsys.readouterr().err
    assert {n: world.journal(n) for n in (feature, epic)} == journals
    _no_drift(world, capsys, feature, epic)


# --- where the walk stops -------------------------------------------------


def test_a_parent_that_cannot_be_read_stops_the_walk_with_a_warning(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    task = _task(world, 99)
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"#99, named as #{task}'s parent, could not be read: gh exited 1. "
        'gh said: "gh: Not Found (HTTP 404)"; the walk stops there.'
    ) in err
    assert f"[warn] forward cascade from #{task}, not completed:" in err
    assert world.views(task) == ("backlog", "backlog")


def test_an_umbrella_cycle_ends_the_walk(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    first = _container(world, "[Umbrella] First")
    second = _container(world, "[Umbrella] Second", first, "Umbrella")
    world.tracker.issues[first]["body"] = f"Umbrella: #{second}\n\n{CONTAINER_BODY}"
    task = _task(world, first, "Umbrella")
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert f"#{second} names #{first} as its parent, which the walk has passed already" in err
    assert world.moves(first) == [("todo", "backlog", "promote-issue")]
    assert world.moves(second) == [("todo", "backlog", "promote-issue")]


def test_a_task_named_as_a_parent_stops_the_walk(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic = _container(world, "[EPIC] An epic")
    other = _task(world, epic, "EPIC")
    task = _task(world, other)
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert f"#{other}, named as #{task}'s parent, is a task, not a container" in err
    assert world.moves(other) == []
    assert world.moves(epic) == []
    assert world.views(other) == ("todo", "todo")


@pytest.mark.parametrize(
    "line", ["Milestone: [#{n}](../milestone/{n})", "Milestone: #{n}"], ids=["link", "plain"]
)
def test_an_epic_under_a_milestone_is_the_top(world: World, line: str) -> None:
    """The issue numbered like the EPIC's milestone is not its parent."""
    bystander = _container(world, "[EPIC] Numbered like the milestone")
    epic = world.file_issue(
        body=f"{line.format(n=bystander)}\n\n{CONTAINER_BODY}", title="[EPIC] An epic", labels=()
    )
    feature = _container(world, "[Feature] A feature", epic, "EPIC")
    task = _task(world, feature)

    assert world.promote(task) == 0

    assert world.moves(epic) == [("todo", "backlog", "promote-issue")]
    assert world.moves(bystander) == []
    assert world.labels(bystander) == []


def test_a_first_line_that_is_no_parent_ref_is_not_followed(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    feature = _container(world, "[Feature] A feature")
    task = _task(world, feature, "Related")
    capsys.readouterr()

    assert world.promote(task) == 0

    assert "[cascade]" not in capsys.readouterr().out
    assert world.moves(feature) == []
    assert world.labels(feature) == []


def test_a_native_parent_other_than_the_first_lines_stops_the_walk(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    named = _container(world, "[EPIC] Named on the first line")
    native = _container(world, "[EPIC] The native parent")
    feature = _container(world, "[Feature] A feature", named, "EPIC")
    world.tracker.native_parents[feature] = native
    task = _task(world, feature)
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"#{feature}'s first line names #{named}, its native parent is #{native}; "
        "nothing is written to either; the walk stops there."
    ) in err
    assert world.moves(feature) == [("todo", "backlog", "promote-issue")]
    assert world.moves(named) == world.moves(native) == []
    assert world.labels(named) == world.labels(native) == []


def test_a_native_parent_that_agrees_with_the_first_line_is_followed(world: World) -> None:
    epic, feature, task = _epic_feature_task(world)
    world.tracker.native_parents[feature] = epic
    world.tracker.native_parents[task] = feature

    assert world.promote(task) == 0

    assert world.moves(epic) == [("todo", "backlog", "promote-issue")]


def test_an_ancestor_whose_type_cannot_be_told_is_moved_as_before(world: World) -> None:
    """A brownfield container with no `[Type]` prefix and no type label: moved,
    and its own first line read as it always was."""
    epic = _container(world, "[EPIC] An epic")
    brownfield = world.file_issue(
        body=f"Parent: #{epic}\n\n{CONTAINER_BODY}", title="Payments work", labels=()
    )
    task = _task(world, brownfield)

    assert world.promote(task) == 0

    assert world.moves(brownfield) == [("todo", "backlog", "promote-issue")]
    assert world.moves(epic) == [("todo", "backlog", "promote-issue")]


# --- the engine is asked only about an ancestor about to move ---------------


def test_a_sibling_starting_under_started_parents_asks_the_engine_nothing_about_them(
    world: World,
) -> None:
    epic, feature, task = _epic_feature_task(world)
    assert world.promote(task) == 0
    assert world.move(task, "in-progress") == 0
    sibling = _task(world, feature, state="backlog")
    world.engine_calls.clear()
    world.tracker.calls.clear()

    assert world.move(sibling, "in-progress") == 0

    assert _ancestor_engine_calls(world, feature, epic) == []
    # Each ancestor is read once, through the read that carries its native parent.
    assert world.tracker.reads(feature) == 1
    assert world.tracker.reads(epic) == 1


def test_an_ancestor_a_sibling_moved_since_the_plan_is_not_moved_twice(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A sibling starts between this move's plan and its cascade: the engine
    places the ancestors in progress already, so nothing more is written or
    journaled, and no entry from a state to itself."""
    epic, feature, task = _epic_feature_task(
        world, epic="backlog", feature="backlog", task="backlog"
    )
    sibling = _task(world, feature, state="backlog")
    label_write = world.mi._gh_apply_state_label

    def sibling_starts_first(number, plan, config):
        if number == task and not world.moves(sibling):
            assert world.move(sibling, "in-progress") == 0
        return label_write(number, plan, config)

    monkeypatch.setattr(world.mi, "_gh_apply_state_label", sibling_starts_first)
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    out = capsys.readouterr().out
    assert f"  #{feature}: left alone at in-progress (the engine's reading)\n" in out
    for number in (feature, epic):
        assert world.moves(number) == [("backlog", "in-progress", "start-work")]
        assert [e["reason"] for e in world.journal(number)] == [
            _reason(sibling, "backlog → in-progress")
        ]
        assert world.labels(number) == ["state:in-progress"]


def test_an_ancestor_the_engine_cannot_place_is_not_written_and_ends_the_walk(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic = _container(world, "[EPIC] An epic")
    outer = _container(world, "[Umbrella] Outer", epic, "EPIC")
    inner = _container(world, "[Umbrella] Inner", outer, "Umbrella")
    task = _task(world, inner, "Umbrella")
    world.tracker.views_fail.add(outer)
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"  #{outer}: not moved: the engine cannot tell where it is, so the walk stops here\n"
        f"  #{epic}: not reached\n"
    ) in err
    assert world.moves(inner) == [("todo", "backlog", "promote-issue")]
    assert world.labels(outer) == world.labels(epic) == []
    assert world.views(task)[0] == "backlog"


def test_an_unreachable_engine_leaves_the_local_reading_in_charge(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    epic, feature, task = _epic_feature_task(world)
    monkeypatch.setattr(world.mi, "_engine_status", lambda number: None)

    assert world.promote(task) == 0

    assert world.labels(feature) == world.labels(epic) == ["state:backlog"]


# --- a write that fails ---------------------------------------------------


def test_a_failed_write_on_one_ancestor_does_not_stop_the_others(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world)
    world.tracker.fail_next.add(str(feature))
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"  #{feature}: not moved: todo → backlog not written (the label write failed)\n"
        f"  #{epic}: todo → backlog\n"
    ) in err
    assert f"run `move-issue {task} --to backlog` again" in err
    assert world.labels(feature) == []
    assert world.moves(epic) == [("todo", "backlog", "promote-issue")]

    # Running the move again brings the Feature level and adds nothing to the EPIC.
    assert world.move(task, "backlog") == 0
    assert world.moves(feature) == [("todo", "backlog", "promote-issue")]
    assert world.moves(epic) == [("todo", "backlog", "promote-issue")]


# --- an ancestor in Todo steps through Backlog (#1229) -----------------------

TODO_TO_IN_PROGRESS = [
    ("todo", "backlog", "promote-issue"),
    ("backlog", "in-progress", "start-work"),
]


def test_an_epic_left_in_todo_under_a_started_feature_is_brought_level(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world, feature="in-progress", task="backlog")
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    assert "[warn]" not in capsys.readouterr().err
    assert world.moves(feature) == []
    assert world.moves(epic) == TODO_TO_IN_PROGRESS
    assert world.labels(epic) == ["state:in-progress"]
    _no_drift(world, capsys, epic)


def test_an_ancestor_ends_with_one_state_label_whatever_it_started_with(world: World) -> None:
    """The Feature has no state label, the EPIC carries `state:todo`: the second
    step is computed from the labels the first left, so neither ends with two."""
    epic, feature, task = _epic_feature_task(world, epic="todo", task="backlog")
    assert world.labels(feature) == []

    assert world.move(task, "in-progress") == 0

    assert world.labels(feature) == world.labels(epic) == ["state:in-progress"]
    assert world.moves(feature) == world.moves(epic) == TODO_TO_IN_PROGRESS


def test_a_second_step_that_fails_leaves_the_ancestor_in_backlog_and_a_rerun_finishes_it(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first write lands and the engine does not take its record; the second
    is still attempted, and fails. The EPIC rests in Backlog with that one state
    label, and running the move again takes it on to In Progress."""
    epic = _container(world, "[EPIC] An epic", state="todo")
    task = _task(world, epic, "EPIC", state="backlog")
    label_write, journal = world.mi._gh_apply_state_label, world.mi._journal_move
    failures = {"write": 1, "journal": 1}

    def second_write_fails(number, plan, config):
        if number == epic and plan.add_label == "state:in-progress" and failures["write"]:
            failures["write"] -= 1
            return False
        return label_write(number, plan, config)

    def first_record_refused(number, from_state, to_state, actor, reason=None):
        if (number, from_state, to_state) == (epic, "todo", "backlog") and failures["journal"]:
            failures["journal"] -= 1
            return False
        return journal(number, from_state, to_state, actor, reason=reason)

    monkeypatch.setattr(world.mi, "_gh_apply_state_label", second_write_fails)
    monkeypatch.setattr(world.mi, "_journal_move", first_record_refused)
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    err = capsys.readouterr().err
    assert (
        f"  #{epic}: todo → backlog (not journaled); "
        "backlog → in-progress not written (the label write failed)\n"
    ) in err
    assert f"run `move-issue {task} --to in-progress` again" in err
    assert world.labels(epic) == ["state:backlog"]
    assert world.moves(epic) == []
    assert world.moves(task) == [("backlog", "in-progress", "start-work")]

    assert world.move(task, "in-progress") == 0

    assert world.labels(epic) == ["state:in-progress"]
    assert world.moves(epic) == [("backlog", "in-progress", "start-work")]


def test_a_review_move_brings_a_todo_ancestor_to_in_progress(world: World) -> None:
    epic, feature, task = _epic_feature_task(world, epic="in-progress", task="in-progress")

    assert world.move(task, "review") == 0

    assert world.moves(feature) == TODO_TO_IN_PROGRESS
    assert world.journal(feature)[0]["reason"] == _reason(task, "in-progress → review")
    assert world.moves(epic) == []


def test_an_ancestor_whose_type_cannot_be_told_steps_through_backlog(world: World) -> None:
    epic = _container(world, "[EPIC] An epic")
    brownfield = world.file_issue(
        body=f"Parent: #{epic}\n\n{CONTAINER_BODY}", title="Payments work", labels=()
    )
    task = _task(world, brownfield, state="backlog")

    assert world.move(task, "in-progress") == 0

    assert world.moves(brownfield) == world.moves(epic) == TODO_TO_IN_PROGRESS
    assert world.labels(brownfield) == ["state:in-progress"]


# --- a move to Done ---------------------------------------------------------


@pytest.mark.parametrize("origin", ["todo", "backlog"])
def test_a_wont_do_move_to_done_moves_no_ancestor(
    world: World, capsys: pytest.CaptureFixture[str], origin: str
) -> None:
    epic, feature, task = _epic_feature_task(world, task="" if origin == "todo" else origin)
    capsys.readouterr()

    assert world.move(task, "done") == 0

    out = capsys.readouterr().out
    assert (
        "[cascade] the forward cascade moves no ancestor: "
        f"a move to done from {origin} is a won't-do close."
    ) in out
    assert world.views(task) == ("done", "done")
    assert world.labels(feature) == world.labels(epic) == []
    assert world.moves(feature) == world.moves(epic) == []


def _reviewed_task_merged(world: World, *, closed: bool) -> tuple[int, int, int]:
    """A Task in Review under a Feature and an EPIC still in Todo, its pull
    request merged by another hand — GitHub having closed it already, or not."""
    epic, feature, task = _epic_feature_task(world, task="review")
    world.tracker.merge(50, closes=[task])
    if not closed:
        world.tracker.issues[task]["state"] = "OPEN"
    return epic, feature, task


def test_a_task_done_while_still_open_brings_its_ancestors_to_in_progress(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _reviewed_task_merged(world, closed=False)
    capsys.readouterr()

    assert world.move(task, "done") == 0

    assert "[noop]" not in capsys.readouterr().out
    assert world.moves(task) == [("review", "done", "done-work")]
    for number in (feature, epic):
        assert world.moves(number) == TODO_TO_IN_PROGRESS
        assert world.journal(number)[0]["reason"] == _reason(task, "review → done")
        assert world.labels(number) == ["state:in-progress"]


def test_a_task_the_merge_already_closed_brings_its_ancestors_to_in_progress(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """GitHub closed the Task as the PR merged, so the move to Done finds it
    there and only rewrites its Review label; its ancestors are brought level
    all the same, from the Review the label recorded."""
    epic, feature, task = _reviewed_task_merged(world, closed=True)
    capsys.readouterr()

    assert world.move(task, "done") == 0

    assert "[noop] already at target state" in capsys.readouterr().out
    assert world.labels(task) == ["type:task", "state:done"]
    for number in (feature, epic):
        assert world.moves(number) == TODO_TO_IN_PROGRESS
        assert world.journal(number)[0]["reason"] == _reason(task, "review → done")


def test_an_issue_already_labelled_done_moves_no_ancestor(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """A closed issue whose label says Done already gives no origin to tell a
    finished close from a won't-do one, so the move to Done moves nothing above it."""
    epic, feature, task = _epic_feature_task(world, task="done")
    world.tracker.issues[task]["state"] = "CLOSED"
    capsys.readouterr()

    assert world.move(task, "done") == 0

    out = capsys.readouterr().out
    assert (
        "[cascade] the forward cascade moves no ancestor: "
        f"#{task} already reads done, so whether it closed as completed or as won't-do "
        "cannot be told."
    ) in out
    assert world.moves(feature) == world.moves(epic) == []


# --- what the preview and the closing block say -----------------------------


def test_a_dry_run_prints_each_ancestors_steps_and_writes_nothing(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world, feature="in-progress", task="backlog")
    world.tracker.calls.clear()
    capsys.readouterr()

    assert world.move(task, "in-progress", "--dry-run") == 0

    out = capsys.readouterr().out
    assert (
        "[cascade] forward cascade — each ancestor brought up to in-progress:\n"
        f"  #{feature} (feature): in-progress; left alone\n"
        f"  #{epic} (epic): todo → backlog → in-progress\n"
    ) in out
    assert not [argv for argv in world.tracker.calls if argv[1:3] == ["issue", "edit"]]
    assert world.moves(epic) == []


def test_no_hook_and_no_comment_follows_a_cascaded_move(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    epic, feature, task = _epic_feature_task(world)
    hooks: list[int] = []
    monkeypatch.setattr(
        world.mi, "fire_hooks", lambda name, context, **kw: hooks.append(context["issue"]["number"])
    )

    assert world.promote(task) == 0

    assert hooks == [task]
    assert world.tracker.comments[feature] == world.tracker.comments[epic] == []


def test_a_promotion_confirmed_with_yes_cascades_like_any_other(world: World) -> None:
    """`--yes` without `--bypass` passes the Todo → Backlog gate with no audit
    comment, and the cascade follows it, posting none either."""
    epic, feature, task = _epic_feature_task(world)

    assert world.move(task, "backlog") == 0

    assert world.moves(feature) == world.moves(epic) == [("todo", "backlog", "promote-issue")]
    assert world.journal(feature)[0]["reason"] == _reason(task, "todo → backlog")
    assert all(world.tracker.comments[n] == [] for n in (task, feature, epic))


def test_with_journal_logging_off_the_cascade_warns_of_nothing(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    set_journal_logging(world.engine_repo, enabled=False)
    epic, feature, task = _epic_feature_task(world)

    assert world.promote(task) == 0
    assert world.move(task, "in-progress") == 0

    out, err = capsys.readouterr()
    assert "[warn]" not in err
    assert f"[cascade] forward cascade from #{task}:" in out
    assert world.views(feature) == world.views(epic) == ("in-progress", "in-progress")
    assert world.journal_files() == []


# --- where the kit does not write the state as a label ----------------------


def _with_config(world: World, monkeypatch: pytest.MonkeyPatch, config: dict) -> None:
    read_yaml = world.mi._read_yaml

    def read(path: Path, loader):
        return dict(config) if path.name == "config.yaml" else read_yaml(path, loader)

    monkeypatch.setattr(world.mi, "_read_yaml", read)


def _with_substrate_map(world: World, monkeypatch: pytest.MonkeyPatch, axes: dict) -> None:
    substrate_map = world.mi.axis_labels.SubstrateMap(axes=axes)
    monkeypatch.setattr(world.mi.axis_labels, "load_substrate_map", lambda *a, **kw: substrate_map)


@pytest.mark.parametrize(
    ("carriage", "says"),
    [
        ("board", "state is carried on your Projects-v2 board"),
        ("degrade", "state is carried by nothing"),
        ("label binding without backlog", "the state label binding has no value for 'backlog'"),
    ],
)
def test_the_cascade_does_not_run_where_the_kit_writes_no_state_label(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    carriage: str,
    says: str,
) -> None:
    epic, feature, task = _epic_feature_task(world)
    world.tracker.issues[task]["milestone"] = MILESTONE  # Backlog, by its milestone
    if carriage == "board":
        _with_config(world, monkeypatch, {"has_projects_v2_board": True})
    elif carriage == "degrade":
        _with_substrate_map(world, monkeypatch, {})
    else:
        remap = {"todo": "Inbox", "in-progress": "Doing", "review": "Review", "done": "Done"}
        _with_substrate_map(world, monkeypatch, {"state": {"label": {"remap": remap}}})
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    out = capsys.readouterr().out
    assert f"[cascade] the forward cascade does not run: {says}" in out
    assert out.count("[cascade]") == 1
    assert world.labels(feature) == world.labels(epic) == []
    assert world.moves(feature) == world.moves(epic) == []
