"""project-management under an engine older than `classified` (ADR-062 point 16).

The shipped issue lifecycle detects with one classifier under `mode:
classified`. An engine shipped before the mode cannot evaluate any of its
states, so it cannot tell where an issue is: every state is indeterminate, and
it refuses to record a move. The lifecycle verbs do not stop on that. The
command that moves an issue treats an indeterminate engine position as it
treats an unreachable engine — it infers the state locally and carries on — and
the engine's refusal to record the move leaves a warning carrying its reason
and, where the project keeps a journal, a gap in it.

The older engine is this engine narrowed to the one mode older engines
implement, so its status answer and its refusal are what such an engine says.
The scripts and the engine run against an in-memory GitHub
(`tests/pm_lifecycle_world.py`).
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

from project_kit import process as process_mod
from tests.pm_lifecycle_world import Tracker, World, load_script, make_engine_repo, wire

#: The modes this engine implements, read before any test narrows them.
THIS_ENGINES_MODES = process_mod.DETECTION_MODES

NOT_IMPLEMENTED = (
    "detection mode 'classified' is not implemented by this engine (it implements 'inferred')"
)


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_older_engine")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_older_engine")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_older_engine")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_older_engine")


@pytest.fixture
def world(tmp_path: Path, ci, pi, mi, hist, monkeypatch: pytest.MonkeyPatch) -> World:
    world = World(Tracker(), make_engine_repo(tmp_path), ci, pi, mi, hist)
    wire(world, monkeypatch)
    return world


def test_a_move_under_an_engine_without_the_mode_lands_on_local_inference_and_warns(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    number = world.file_issue()
    assert world.promote(number) == 0
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]
    capsys.readouterr()

    # The engine an older binary ships: it implements `inferred` alone.
    monkeypatch.setattr(process_mod, "DETECTION_MODES", (process_mod.INFERRED,))
    tracker_view, engine_view = world.views(number)
    assert (tracker_view, engine_view) == ("backlog", None)

    assert world.move(number, "in-progress") == 0
    moved = capsys.readouterr()

    # The move landed on the tracker, from the position inferred locally.
    assert world.labels(number) == ["type:task", "state:in-progress"]
    assert world.tracker.state_of(number) == "in-progress"
    # The engine refused to record it, and the warning carries its reason and
    # names the gap it leaves.
    assert "[warn] the process engine refused this move:" in moved.err
    assert "position is indeterminate" in moved.err
    assert NOT_IMPLEMENTED in moved.err
    assert f"`pkit pm history {number} --check-drift` will show the gap" in moved.err
    assert world.moves(number) == [("todo", "backlog", "promote-issue")]

    # Once the binary implements the mode, the engine reads the move and the
    # drift check shows the gap the warning named.
    monkeypatch.setattr(process_mod, "DETECTION_MODES", THIS_ENGINES_MODES)
    assert world.views(number) == ("in-progress", "in-progress")
    assert world.history(number) == 3
