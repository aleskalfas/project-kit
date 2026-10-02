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

import argparse
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from tests.pm_lifecycle_world import (
    AUTHORED_BODY,
    CAPABILITY_ROOT,
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


@pytest.fixture(scope="module")
def cl() -> ModuleType:
    return load_script("close-issue.py", "pm_close_issue_forward_cascade")


@pytest.fixture(scope="module")
def dw() -> ModuleType:
    return load_script("done-work.py", "pm_done_work_forward_cascade")


@pytest.fixture
def engine_repo(tmp_path: Path) -> Path:
    return make_engine_repo(tmp_path)


@pytest.fixture
def world(engine_repo: Path, ci, pi, mi, hist, cl, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), engine_repo, ci, pi, mi, hist, cl)
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


def test_a_feature_under_an_umbrella_is_walked_to_the_epic(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """An Umbrella may hold a Feature, and a Feature's first line may name it
    (#1281): the walk goes through the Feature and the Umbrella to the EPIC."""
    epic = _container(world, "[EPIC] An epic")
    umbrella = _container(world, "[Umbrella] A bucket", epic, "EPIC")
    feature = _container(world, "[Feature] A feature", umbrella, "Umbrella")
    task = _task(world, feature)

    assert world.promote(task) == 0

    assert "the walk stops there" not in capsys.readouterr().err
    for number in (feature, umbrella, epic):
        assert world.moves(number) == [("todo", "backlog", "promote-issue")], number


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
    assert (
        "[noop] already at target state; reconciling labels if needed.\n"
        "  Any ancestor behind it is still brought level, with no prompt: "
        "the forward cascade asks for none.\n"
    ) in out
    assert world.moves(feature) == []
    assert world.moves(epic) == [("backlog", "in-progress", "start-work")]
    assert world.journal(epic)[0]["reason"] == _reason(task, "at in-progress")
    assert world.moves(task) == []


def test_a_dry_run_of_a_move_already_made_previews_the_cascade_and_writes_nothing(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(
        world, epic="backlog", feature="in-progress", task="in-progress"
    )
    world.tracker.calls.clear()
    capsys.readouterr()

    assert world.move(task, "in-progress", "--dry-run") == 0

    out = capsys.readouterr().out
    assert (
        f"  #{feature} (feature): in-progress; left alone\n"
        f"  #{epic} (epic): backlog → in-progress\n"
    ) in out
    assert "[dry-run] nothing written." in out
    assert not [argv for argv in world.tracker.calls if argv[1:3] == ["issue", "edit"]]
    assert world.moves(epic) == []
    assert world.labels(epic) == ["state:backlog"]


def test_a_move_already_made_with_no_cascade_brings_no_ancestor_level(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(
        world, epic="backlog", feature="in-progress", task="in-progress"
    )
    capsys.readouterr()

    assert world.move(task, "in-progress", "--no-cascade") == 0

    out = capsys.readouterr().out
    assert "[noop] already at target state; reconciling labels if needed.\n" in out
    assert "brought level" not in out
    assert "[cascade]" not in out
    assert world.moves(feature) == world.moves(epic) == []
    assert world.labels(epic) == ["state:backlog"]


@pytest.mark.parametrize("levels", [None, []], ids=["missing", "empty"])
def test_a_workflow_naming_no_cascade_level_is_said_not_read_as_no_container(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    levels: list[str] | None,
) -> None:
    read_yaml = world.mi._read_yaml

    def read(path: Path, loader):
        data = read_yaml(path, loader)
        if path.name == "workflow.yaml":
            forward = dict(data["cascade"]["forward"])
            if levels is None:
                del forward["applies_to_levels"]
            else:
                forward["applies_to_levels"] = levels
            data = {**data, "cascade": {**data["cascade"], "forward": forward}}
        return data

    monkeypatch.setattr(world.mi, "_read_yaml", read)
    epic, feature, task = _epic_feature_task(world)
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        "[warn] the forward cascade does not run: workflow.yaml declares no "
        "`cascade.forward.applies_to_levels`, so which issue types it moves is not known.\n"
    ) in err
    assert world.moves(feature) == world.moves(epic) == []


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


TASK_FORMS = "Feature: #<N> or Umbrella: #<N> or EPIC: #<N> or Milestone: [#<N>](../milestone/<N>)"


@pytest.mark.parametrize("line", ["Related: #{n}", "Epic: #{n}", "Feature: #{n} — auth"])
def test_a_first_line_that_is_not_an_allowed_parent_ref_is_said_and_not_followed(
    world: World, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    feature = _container(world, "[Feature] A feature")
    written = line.format(n=feature)
    task = world.file_issue(body=f"{written}\n\n{AUTHORED_BODY}")
    capsys.readouterr()

    assert world.promote(task) == 0

    out, err = capsys.readouterr()
    assert "[cascade]" not in out
    assert (
        f"[warn] #{task}'s first line `{written}` is not a parent-ref a task may have: "
        f"{TASK_FORMS}; the forward cascade walks nothing from it.\n"
    ) in err
    assert world.moves(feature) == []
    assert world.labels(feature) == []


def test_an_ancestors_first_line_that_is_not_an_allowed_form_stops_the_walk_above_it(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic = _container(world, "[EPIC] An epic")
    feature = _container(world, "[Feature] A feature", epic, "Epic")
    task = _task(world, feature)
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"the walk stopped: #{feature}'s first line `Epic: #{epic}` is not a parent-ref a "
        "feature may have: EPIC: #<N> or Umbrella: #<N> or Milestone: [#<N>](../milestone/<N>)\n"
    ) in err
    assert world.moves(feature) == [("todo", "backlog", "promote-issue")]
    assert world.moves(epic) == []


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
        "nothing is written to either parent; the walk stops there.\n"
        f"  → the native parent wins (DEC-005): `set-field {feature} --parent {native}` "
        f"rewrites #{feature}'s first line to name it.\n"
    ) in err
    assert (
        f"  → run `move-issue {task} --to backlog` again once the cause is fixed: "
        "the cascade is idempotent, and brings level what is still behind.\n"
    ) in err
    # The ancestor whose two parents disagree is moved; nothing above it is.
    assert world.moves(feature) == [("todo", "backlog", "promote-issue")]
    assert world.moves(named) == world.moves(native) == []
    assert world.labels(named) == world.labels(native) == []


def test_a_native_parent_that_agrees_with_the_first_line_is_followed(world: World) -> None:
    epic, feature, task = _epic_feature_task(world)
    world.tracker.native_parents[feature] = epic
    world.tracker.native_parents[task] = feature

    assert world.promote(task) == 0

    assert world.moves(feature) == world.moves(epic) == [("todo", "backlog", "promote-issue")]


# --- the moved issue's own parent is held to its native one ----------------


def test_a_moved_issue_whose_native_parent_is_not_its_first_lines_walks_nowhere(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """A Task re-parented in GitHub's UI: its first line still names the old
    Feature. Neither Feature's chain is moved."""
    epic, named, task = _epic_feature_task(world)
    native = _container(world, "[Feature] Where the task was moved to", epic, "EPIC")
    world.tracker.native_parents[task] = native
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"[warn] the forward cascade walks nothing: #{task}'s first line names #{named}, "
        f"its native parent is #{native}; nothing is written to either parent.\n"
        f"  → the native parent wins (DEC-005): `set-field {task} --parent {native}` "
        f"rewrites #{task}'s first line to name it.\n"
        f"  → run `move-issue {task} --to backlog` again once the two agree: the cascade is "
        "idempotent, and brings level what is still behind.\n"
    ) in err
    assert world.views(task) == ("backlog", "backlog")
    for number in (named, native, epic):
        assert world.moves(number) == []
        assert world.labels(number) == []


def test_a_native_parent_under_a_first_line_that_names_none_walks_nowhere(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    feature = _container(world, "[Feature] A feature")
    task = world.file_issue()
    world.tracker.native_parents[task] = feature
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"[warn] the forward cascade walks nothing: #{task}'s first line names no parent "
        f"issue, its native parent is #{feature}; nothing is written to #{feature}.\n"
        f"  → the native parent wins (DEC-005): `set-field {task} --parent {feature}` "
        f"rewrites #{task}'s first line to name it.\n"
    ) in err
    assert world.moves(feature) == []
    assert world.labels(feature) == []


def test_a_native_parent_in_another_repository_walks_nowhere(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world)
    world.tracker.native_parents[task] = "other/repo#7"
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"[warn] the forward cascade walks nothing: #{task}'s first line names #{feature}, "
        "its native parent is other/repo#7; nothing is written to either parent.\n"
        "  → other/repo#7 is in another repository, which no first-line form can name and "
        f"the forward cascade does not walk into; if #{feature} is its parent, "
        f"`set-field {task} --parent {feature}` moves the native link under it.\n"
    ) in err
    assert world.moves(feature) == world.moves(epic) == []
    assert world.labels(feature) == world.labels(epic) == []


def test_a_moved_issue_whose_record_cannot_be_read_walks_nowhere(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world)
    read = world.mi.containment.read_issue_record

    def unreadable_task(config, *, issue_number):
        if issue_number == task:
            return world.mi.containment.UnreadIssue("gh exited 1")
        return read(config, issue_number=issue_number)

    monkeypatch.setattr(world.mi.containment, "read_issue_record", unreadable_task)
    capsys.readouterr()

    assert world.promote(task) == 0

    err = capsys.readouterr().err
    assert (
        f"[warn] the forward cascade walks nothing: #{task}'s record could not be read to "
        f"hold its native parent to #{feature}, the parent its first line names "
        "(gh exited 1).\n"
    ) in err
    assert world.moves(feature) == world.moves(epic) == []


def test_the_moved_issues_record_is_read_once_and_only_where_a_cascade_runs(
    world: World,
) -> None:
    epic, feature, task = _epic_feature_task(world, task="backlog")
    world.tracker.calls.clear()

    def record_reads() -> int:
        record = f"repos/{{owner}}/{{repo}}/issues/{task}"
        return sum(1 for argv in world.tracker.calls if argv[1] == "api" and argv[-1] == record)

    assert world.move(task, "in-progress", "--no-cascade") == 0
    assert record_reads() == 0

    assert world.move(task, "review") == 0
    assert record_reads() == 1
    assert world.moves(feature) == world.moves(epic) == TODO_TO_IN_PROGRESS


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
    # The engine's cause, and what its classifier said, under the ancestor (#1244).
    assert (
        f"  #{outer}: not moved: the engine cannot tell where it is, so the walk stops here\n"
        "    couldn't evaluate detection predicate 'detect-state': it exited 2\n"
        "      the predicate said:\n"
        f"        could not read issue #{outer}: `gh issue view` exited 1\n"
        "        HTTP 502: Bad Gateway\n"
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


def test_an_engine_that_exits_non_zero_for_one_ancestor_has_the_plan_written_for_it(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`pkit process status` fails for the Feature alone: the Feature is moved as
    the plan read it from its labels, and the EPIC as the engine places it."""
    epic, feature, task = _epic_feature_task(world, task="backlog")
    run = world.run

    def status_fails_for_the_feature(argv, *args, **kwargs):
        argv = [str(arg) for arg in argv]
        if argv[:3] == ["pkit", "process", "status"] and str(feature) in argv:
            return subprocess.CompletedProcess(argv, 1, "", "engine: boom")
        return run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", status_fails_for_the_feature)
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    assert "[warn]" not in capsys.readouterr().err
    for number in (feature, epic):
        assert world.moves(number) == TODO_TO_IN_PROGRESS
        assert world.labels(number) == ["state:in-progress"]


def _between_plan_and_write(world: World, monkeypatch: pytest.MonkeyPatch, task: int, act) -> None:
    """Run `act` once, after the cascade's plan is read and before its first
    ancestor write — at the moved issue's own label write."""
    label_write = world.mi._gh_apply_state_label
    pending = [act]

    def act_first(number, plan, config):
        if number == task and pending:
            pending.pop()()
        return label_write(number, plan, config)

    monkeypatch.setattr(world.mi, "_gh_apply_state_label", act_first)


def test_an_ancestor_moved_since_the_plan_and_still_behind_is_written_from_its_labels_now(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A sibling is promoted between this move's plan and its cascade: the engine
    places the Feature in Backlog, not the Todo the plan read, so the Feature is
    read again and taken on from Backlog alone."""
    epic, feature, task = _epic_feature_task(world, epic="in-progress", task="backlog")
    sibling = _task(world, feature)
    _between_plan_and_write(world, monkeypatch, task, lambda: world.promote(sibling))
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    out = capsys.readouterr().out
    assert f"  #{feature} (feature): todo → backlog → in-progress\n" in out  # the plan
    assert f"  #{feature}: backlog → in-progress\n" in out  # what was written
    assert world.moves(feature) == TODO_TO_IN_PROGRESS
    assert [e["reason"] for e in world.journal(feature)] == [
        _reason(sibling, "todo → backlog"),
        _reason(task, "backlog → in-progress"),
    ]
    assert world.labels(feature) == ["state:in-progress"]
    assert world.moves(epic) == []


def test_an_ancestor_moved_since_the_plan_that_cannot_be_read_again_is_not_written(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world, epic="in-progress", task="backlog")
    sibling = _task(world, feature)
    read = world.mi.containment.read_issue_record
    armed: list[bool] = []

    def read_again_fails(config, *, issue_number):
        if issue_number == feature and armed:
            armed.clear()
            return world.mi.containment.UnreadIssue("gh exited 1")
        return read(config, issue_number=issue_number)

    def sibling_promoted() -> None:
        assert world.promote(sibling) == 0
        armed.append(True)  # the Feature's next read is this move's read again

    monkeypatch.setattr(world.mi.containment, "read_issue_record", read_again_fails)
    _between_plan_and_write(world, monkeypatch, task, sibling_promoted)
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    err = capsys.readouterr().err
    assert (
        f"  #{feature}: not moved: the engine places it at backlog and it could not be read "
        "again (gh exited 1)\n"
    ) in err
    assert f"run `move-issue {task} --to in-progress` again" in err
    assert world.moves(feature) == [("todo", "backlog", "promote-issue")]
    assert world.labels(feature) == ["state:backlog"]
    assert world.moves(epic) == []


def test_a_parent_closed_between_plan_and_write_is_left_alone(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    epic, feature, task = _epic_feature_task(world, task="backlog")
    _between_plan_and_write(
        world, monkeypatch, task, lambda: world.tracker.close(feature, "NOT_PLANNED")
    )
    capsys.readouterr()

    assert world.move(task, "in-progress") == 0

    out = capsys.readouterr().out
    assert f"  #{feature}: left alone at done (the engine's reading)\n" in out
    assert world.moves(feature) == []
    assert world.labels(feature) == []
    assert world.moves(epic) == TODO_TO_IN_PROGRESS


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


def test_an_ancestor_with_no_state_label_or_a_todo_label_ends_with_one_state_label(
    world: World,
) -> None:
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


def _done_task(world: World, reason: str | None) -> tuple[int, int, int]:
    """A Task whose label already reads Done, closed with close reason `reason`
    (None: the tracker reports none), under a Feature and an EPIC in Todo."""
    epic, feature, task = _epic_feature_task(world, task="done")
    world.tracker.close(task, reason)
    return epic, feature, task


def test_an_issue_labelled_done_and_closed_as_completed_brings_its_ancestors_level(
    world: World,
) -> None:
    epic, feature, task = _done_task(world, "COMPLETED")

    assert world.move(task, "done") == 0

    for number in (feature, epic):
        assert world.moves(number) == TODO_TO_IN_PROGRESS
        assert world.journal(number)[0]["reason"] == _reason(task, "at done")


@pytest.mark.parametrize(
    ("reason", "said"), [("NOT_PLANNED", "not planned"), ("DUPLICATE", "duplicate")]
)
def test_an_issue_labelled_done_and_closed_otherwise_moves_no_ancestor(
    world: World, capsys: pytest.CaptureFixture[str], reason: str, said: str
) -> None:
    epic, feature, task = _done_task(world, reason)
    capsys.readouterr()

    assert world.move(task, "done") == 0

    out = capsys.readouterr().out
    assert (
        "[cascade] the forward cascade moves no ancestor: "
        f"#{task} closed as {said}, not as completed."
    ) in out
    assert world.moves(feature) == world.moves(epic) == []


@pytest.mark.parametrize("closed", [True, False], ids=["closed", "open"])
def test_an_issue_labelled_done_with_no_close_reason_moves_no_ancestor_and_says_what_will(
    world: World, capsys: pytest.CaptureFixture[str], closed: bool
) -> None:
    """Closed where the tracker reports no reason, or still open with a Done
    label: completion cannot be told from won't-do, and running the move again
    would not tell it either, so that is not advised."""
    epic, feature, task = _epic_feature_task(world, task="done")
    if closed:
        world.tracker.close(task, None)
    capsys.readouterr()

    assert world.move(task, "done") == 0

    out, err = capsys.readouterr()
    assert (
        "[cascade] the forward cascade moves no ancestor: "
        f"#{task} already reads done and no close reason is reported for it, so whether it "
        "was completed or dropped as won't-do cannot be told; the next forward move under "
        "its ancestors brings them level."
    ) in out
    assert "again" not in out + err
    assert world.moves(feature) == world.moves(epic) == []


def test_a_cascade_cut_short_on_a_merged_task_is_finished_by_running_the_move_again(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """The merge closed the Task as completed; the move to Done rewrites its
    Review label and cascades, and the Feature's write fails. Running the move
    again finds the label at Done, reads the close reason, and finishes."""
    epic, feature, task = _reviewed_task_merged(world, closed=True)
    world.tracker.fail_next.add(str(feature))
    capsys.readouterr()

    assert world.move(task, "done") == 0

    err = capsys.readouterr().err
    assert (
        f"  → run `move-issue {task} --to done` again once the cause is fixed: the cascade "
        "is idempotent, and brings level what is still behind.\n"
    ) in err
    assert world.labels(feature) == []
    assert world.labels(task) == ["type:task", "state:done"]

    assert world.move(task, "done") == 0

    assert world.moves(feature) == world.moves(epic) == TODO_TO_IN_PROGRESS
    assert world.journal(feature)[0]["reason"] == _reason(task, "at done")


def test_a_cascade_cut_short_on_an_open_task_is_finished_once_it_has_closed(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """Moved Review → Done while still open, the Task's re-run finishes the
    cascade only once it has closed as completed, and the advice says so."""
    epic, feature, task = _reviewed_task_merged(world, closed=False)
    world.tracker.fail_next.add(str(feature))
    capsys.readouterr()

    assert world.move(task, "done") == 0

    assert (
        f"  → run `move-issue {task} --to done` again once the cause is fixed and #{task} has "
        "closed as completed: the cascade is idempotent, and brings level what is still "
        "behind.\n"
    ) in capsys.readouterr().err
    assert world.moves(epic) == TODO_TO_IN_PROGRESS  # the walk went on above the Feature

    # Still open, the Task's label reads Done and its finish cannot be told yet.
    assert world.move(task, "done") == 0
    assert world.moves(feature) == []

    world.tracker.close(task, "COMPLETED")
    assert world.move(task, "done") == 0

    assert world.moves(feature) == TODO_TO_IN_PROGRESS


def test_the_line_done_work_prints_when_the_move_to_done_fails_finishes_the_cascade(
    world: World,
    dw: ModuleType,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The merge closed the Task; done-work's move to Done fails at the label
    reconcile, before any cascade, and close-issue then writes the Done label.
    The line done-work prints is a command that runs, and running it brings the
    Task's ancestors level."""
    epic, feature, task = _reviewed_task_merged(world, closed=True)
    monkeypatch.setattr(dw.pr_merge, "delete_branch", lambda *a, **kw: "deleted")
    monkeypatch.setattr(dw.pr_merge, "cleanup_local", lambda *a, **kw: None)
    world.tracker.fail_next.add("state:review")  # the reconcile removes the Review label
    capsys.readouterr()

    run = dw._after_merge(
        argparse.Namespace(
            issue_number=task, capability_root=CAPABILITY_ROOT, skip_checkbox_gate=False
        ),
        pr_number=50,
        to_close=[task],
        branch=f"fix/{task}-a-task",
        cross=False,
        merged_head="0" * 40,
        confirmed=False,
        config={},
    )

    assert run.exit_code == 3
    assert world.labels(task) == ["type:task", "state:done"]  # close-issue wrote it
    assert world.moves(feature) == world.moves(epic) == []
    line = f"re-run `move-issue {task} --to done` to complete the lifecycle transition"
    assert line in capsys.readouterr().err

    assert world.move(task, "done") == 0

    assert world.moves(feature) == world.moves(epic) == TODO_TO_IN_PROGRESS


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
