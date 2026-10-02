"""What project-management passes on of a predicate the engine could not evaluate (#1244).

The engine says why a predicate could not be evaluated: a reason naming how its
run ended, and what it wrote on standard error, bounded and stripped of escape
sequences — `stderr_tail` in its JSON views, under "the predicate said:" in its
narrative ones. The pm verbs that report the engine's answer pass both on:

- `close-issue --mode=cascade-eligibility-close`, holding a container whose
  fold the engine could not resolve, prints the fold's reason and the words;
- `move-issue`'s forward cascade, stopping at an ancestor the engine cannot
  place, prints why under that ancestor;
- the warning a move the engine refused to record leaves prints the engine's
  causes and the words after its own sentence, never run on into them.

Verdicts and exit codes are unchanged. Each surface meets a predicate that
cannot start, one that prints something other than JSON, and one that exits
with an escape-laden standard error. The predicate runs as a real script under
the engine's own runner; everything else runs the real scripts and the real
engine against an in-memory GitHub (`tests/pm_lifecycle_world.py`).
"""

from __future__ import annotations

import stat
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from project_kit.process import PredicateRunner
from tests.pm_lifecycle_world import (
    AUTHORED_BODY,
    Tracker,
    World,
    answer_from_tracker,
    load_script,
    make_engine_repo,
    wire,
)

#: The runner's own predicate run, before any test routes it through the tracker.
_RUN_THE_SCRIPT = PredicateRunner._invoke

ENGINE_WARNING = "the process engine refused this move"

# Clears the screen, retitles the window, colours a word, writes a NUL and
# exits 2: what reaches the operator is the words alone.
_ESCAPE_LADEN = (
    "import sys\n"
    "sys.stderr.buffer.write(b'\\x1b[2J\\x1b]0;pwned\\x07tracker \\x1b[31mdown\\x1b[0m\\x00\\n')\n"
    "sys.exit(2)\n"
)

#: How each predicate is broken: its script's body (None: not executable, so it
#: cannot start), how the engine names the ending, and what it said.
BROKEN = [
    pytest.param(None, "could not start: [Errno 13] Permission denied", None, id="cannot-start"),
    pytest.param(
        "print('not json at all')\n",
        "printed no JSON document on its standard output",
        None,
        id="garbage",
    ),
    pytest.param(_ESCAPE_LADEN, "exited 2", "tracker down", id="escape-laden"),
]


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_engine_said")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_engine_said")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_engine_said")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_engine_said")


@pytest.fixture(scope="module")
def cl() -> ModuleType:
    return load_script("close-issue.py", "pm_close_issue_engine_said")


@pytest.fixture
def world(tmp_path: Path, ci, pi, mi, hist, cl, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), make_engine_repo(tmp_path), ci, pi, mi, hist, cl)
    wire(world, monkeypatch)
    return world


def _break(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    body: str | None,
    for_subject: Callable[[str], bool] = lambda _subject: True,
) -> None:
    """Make the engine run `command` as a real script for the subjects
    `for_subject` picks — `body`, or, for None, a script that is not executable —
    while every other predicate run answers from the tracker as before."""
    script = world.engine_repo / ".pkit/capabilities/project-management/scripts" / f"{command}.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("#!/usr/bin/env python3\n" + (body or "print('{}')\n"), encoding="utf-8")
    if body is not None:
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def invoke(runner: PredicateRunner, run_name: str, with_args: Any) -> Any:
        if run_name == command and for_subject(runner.subject):
            return _RUN_THE_SCRIPT(runner, run_name, with_args)
        return answer_from_tracker(runner, run_name, with_args)

    monkeypatch.setattr(PredicateRunner, "_invoke", invoke)


def _said(said: str | None, indent: str) -> str:
    """The words under their attribution, as the engine's narrative lays them."""
    return "" if said is None else f"{indent}the predicate said:\n{indent}  {said}\n"


def _assert_nothing_raw_reaches(err: str) -> None:
    assert "pwned" not in err
    assert not any(ch in err for ch in "\x00\x07\x1b")


# --- close-issue: the held fold ------------------------------------------------


def _container(world: World) -> int:
    """A Feature its child's start has cascaded to In Progress."""
    parent = world.file_issue(title="[Feature] A feature", labels=())
    child = world.file_issue(body=f"Feature: #{parent}\n\n{AUTHORED_BODY}")
    assert world.promote(child) == 0
    assert world.move(child, "in-progress") == 0
    return parent


@pytest.mark.parametrize(("body", "cause", "said"), BROKEN)
def test_a_held_fold_prints_what_the_members_predicate_said(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str | None,
    cause: str,
    said: str | None,
) -> None:
    parent = _container(world)
    _break(world, monkeypatch, "cascade-members", body)
    capsys.readouterr()

    assert world.close(parent, "--mode", "cascade-eligibility-close") == 1  # held, as before

    err = capsys.readouterr().err
    assert (
        f"  → could not read cascade members for parent '{parent}' (the `members` predicate {cause}"
    ) in err
    assert (
        "); failing closed\n"
        + _said(said, "    ")
        + "  → re-run once `gh` is reachable and every child's state is readable"
    ) in err
    _assert_nothing_raw_reaches(err)
    assert world.tracker.state_of(parent) == "in-progress"


# --- move-issue: an ancestor the engine cannot place ---------------------------


@pytest.mark.parametrize(("body", "cause", "said"), BROKEN)
def test_the_cascade_says_why_the_engine_cannot_place_an_ancestor(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str | None,
    cause: str,
    said: str | None,
) -> None:
    epic = world.file_issue(title="[EPIC] An epic", labels=())
    feature = world.file_issue(
        title="[Feature] A feature", body=f"EPIC: #{epic}\n\n## What\n\nA feature.\n", labels=()
    )
    task = world.file_issue(body=f"Feature: #{feature}\n\n{AUTHORED_BODY}")
    _break(world, monkeypatch, "detect-state", body, lambda subject: subject == str(feature))
    capsys.readouterr()

    assert world.promote(task) == 0  # the issue's own move stands, as before

    err = capsys.readouterr().err
    assert (
        f"  #{feature}: not moved: the engine cannot tell where it is, so the walk stops here\n"
        f"    couldn't evaluate detection predicate 'detect-state': it {cause}"
    ) in err
    if said is not None:
        assert f": it {cause}\n" + _said(said, "      ") + f"  #{epic}: not reached\n" in err
    else:
        assert "the predicate said:" not in err
    _assert_nothing_raw_reaches(err)
    assert world.labels(feature) == world.labels(epic) == []
    assert world.tracker.state_of(task) == "backlog"


# --- the warning a move the engine refused to record leaves --------------------


@pytest.mark.parametrize(("body", "cause", "said"), BROKEN)
def test_a_refused_record_s_warning_carries_the_predicate_s_words_on_their_own_lines(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str | None,
    cause: str,
    said: str | None,
) -> None:
    number = world.file_issue()
    assert world.promote(number) == 0
    _break(world, monkeypatch, "detect-state", body)
    capsys.readouterr()

    # The engine cannot tell where the issue is: move-issue moves it on its own
    # reading, and the engine refuses to record the move.
    assert world.move(number, "in-progress") == 0

    err = capsys.readouterr().err
    assert world.tracker.state_of(number) == "in-progress"
    warning = next(line for line in err.splitlines() if ENGINE_WARNING in line)
    assert warning.startswith(
        f"  [warn] {ENGINE_WARNING}: refused: position is indeterminate — a detection "
        "predicate could not be evaluated; refusing to move (fail-closed). "
    )
    assert warning.endswith("The label/position is unaffected.")
    assert (
        f"{warning}\n"
        "    'done', 'review', 'in-progress', 'backlog', 'todo': couldn't evaluate "
        f"detection predicate 'detect-state': it {cause}"
    ) in err
    if said is not None:
        assert f": it {cause}\n" + _said(said, "      ") in err
    _assert_nothing_raw_reaches(err)
