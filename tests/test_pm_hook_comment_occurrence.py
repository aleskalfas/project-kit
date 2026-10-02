"""A hook's comment posts again when the same transition happens again (#1243).

A `post-comment` hook opens its comment with a stamp naming the firing it
posted for (#950): the hook, the event, the issue and, on a move, the from and
to states. An issue that made a transition a second time, or was closed again
after a reopen, matched its first firing's stamp, and the comment was dropped
as a retry. A firing now includes which occurrence it is: `move-issue` names it
by the issue's count of landed moves, `close-issue` by when the issue was
closed. A re-run of the same move or the same close names the same occurrence
and posts nothing new.

These tests run the real scripts, the real hook engine and the real process
engine against an in-memory GitHub (`tests/pm_lifecycle_world.py`).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.pm_lifecycle_world import (
    CAPABILITY_ROOT,
    INVOKER,
    Tracker,
    World,
    load_script,
    make_engine_repo,
    wire,
)
from tests.process_journal_support import set_journal_logging

# The engine the scripts import, from the `scripts/` directory the world puts on
# the path.
HOOKS = importlib.import_module("_lib.hooks")

MOVED = "moved"
CLOSED = "closed"
PR = 500
WONT_DO = "superseded by #99"

#: Whether the project keeps a journal, which decides what counts the moves.
JOURNAL = [pytest.param(True, id="journal"), pytest.param(False, id="no-journal")]


@pytest.fixture(scope="module")
def ci() -> ModuleType:
    return load_script("create-issue.py", "pm_create_issue_hook_occurrence")


@pytest.fixture(scope="module")
def pi() -> ModuleType:
    return load_script("promote-issue.py", "pm_promote_issue_hook_occurrence")


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return load_script("move-issue.py", "pm_move_issue_hook_occurrence")


@pytest.fixture(scope="module")
def hist() -> ModuleType:
    return load_script("history.py", "pm_history_hook_occurrence")


@pytest.fixture(scope="module")
def cl() -> ModuleType:
    return load_script("close-issue.py", "pm_close_issue_hook_occurrence")


@pytest.fixture(scope="module")
def ro() -> ModuleType:
    return load_script("reopen-issue.py", "pm_reopen_issue_hook_occurrence")


@pytest.fixture
def engine_repo(tmp_path: Path) -> Path:
    return make_engine_repo(tmp_path)


@pytest.fixture
def hook_root(tmp_path: Path) -> Path:
    """A capability tree whose `hooks.yaml` declares one `post-comment` hook on
    `after_move_issue` and one on `after_close_issue`."""
    root = tmp_path / "hooks"
    templates = root / "project" / "hook-templates"
    templates.mkdir(parents=True)
    templates.joinpath(f"{MOVED}.md").write_text(
        "#{{ issue.number }} moved to {{ transition.to }}", encoding="utf-8"
    )
    templates.joinpath(f"{CLOSED}.md").write_text("#{{ issue.number }} closed", encoding="utf-8")
    (root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_move_issue:\n"
        "    - kind: post-comment\n"
        f"      template_path: project/hook-templates/{MOVED}.md\n"
        "  after_close_issue:\n"
        "    - kind: post-comment\n"
        f"      template_path: project/hook-templates/{CLOSED}.md\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def fired() -> list[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Each `fire_hooks` call a script made: (event, context, config, options)."""
    return []


@pytest.fixture
def world(
    engine_repo: Path,
    ci,
    pi,
    mi,
    hist,
    cl,
    ro,
    hook_root: Path,
    fired: list,
    monkeypatch: pytest.MonkeyPatch,
) -> World:
    world = World(Tracker(), engine_repo, ci, pi, mi, hist, cl)
    wire(world, monkeypatch)

    # The hooks fire for real, as the scripts call them, from this test's
    # `hooks.yaml` rather than the capability's.
    def fire_hooks(event, context, config, *, capability_root=None, **options):
        options["capability_root"] = hook_root
        fired.append((event, context, config, options))
        return HOOKS.fire_hooks(event, context, config, **options)

    for script in (mi, cl):
        monkeypatch.setattr(script, "fire_hooks", fire_hooks)
    monkeypatch.setattr(ro, "resolve_invoker_identity", lambda config=None: INVOKER)
    return world


def _reopen(ro: ModuleType, number: int, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(
        sys,
        "argv",
        ["reopen-issue.py", str(number), "--capability-root", str(CAPABILITY_ROOT), "--yes"],
    )
    return ro.main()


def _stamps(world: World, number: int, says: str) -> list[str]:
    """The stamps of the hook comments on the issue that say `says`, oldest first."""
    stamps = []
    for comment in world.tracker.comments[number]:
        stamp, _, text = comment["body"].partition("\n\n")
        if stamp.startswith(HOOKS.HOOK_STAMP_OPEN) and text == says:
            stamps.append(stamp)
    return stamps


def _reads(world: World, number: int, field: str) -> int:
    """How many times the issue was read for `field` alone."""
    return world.tracker.calls.count(["gh", "issue", "view", str(number), "--json", field])


def _started(world: World) -> int:
    number = world.file_issue()
    assert world.promote(number) == 0
    assert world.move(number, "in-progress") == 0
    return number


def _merged(world: World) -> int:
    """A Task whose pull request merged: GitHub closed it, its Review label left."""
    number = _started(world)
    assert world.move(number, "review") == 0
    world.tracker.merge(PR, [number])
    return number


# --- a transition made again ----------------------------------------------------


@pytest.mark.parametrize("journal", JOURNAL)
def test_the_same_transition_made_again_posts_again(
    world: World, ro: ModuleType, monkeypatch: pytest.MonkeyPatch, journal: bool
) -> None:
    """The Task goes Todo → Backlog → In Progress → Review, is merged, closed and
    reopened, and makes the same three moves again: each posts its own comment."""
    if not journal:
        set_journal_logging(world.engine_repo, enabled=False)
    number = _merged(world)
    assert world.close(number, "--mode", "pr-merge") == 0
    assert _reopen(ro, number, monkeypatch) == 0

    assert world.promote(number) == 0
    assert world.move(number, "in-progress") == 0
    assert world.move(number, "review") == 0

    for state in ("backlog", "in-progress", "review"):
        stamps = _stamps(world, number, f"#{number} moved to {state}")
        assert len(stamps) == 2, state
        assert stamps[0] != stamps[1], state


def test_a_rerun_of_the_same_move_posts_nothing_new(world: World) -> None:
    number = _started(world)
    assert world.move(number, "review") == 0

    assert world.move(number, "review") == 0

    assert len(_stamps(world, number, f"#{number} moved to review")) == 1


@pytest.mark.parametrize("journal", JOURNAL)
def test_the_same_firing_again_posts_nothing_new(world: World, fired: list, journal: bool) -> None:
    """The occurrence `move-issue` names stays the same for the move it fired
    on, so firing its hooks again for that move finds the comment posted."""
    if not journal:
        set_journal_logging(world.engine_repo, enabled=False)
    number = _started(world)
    assert world.move(number, "review") == 0
    event, context, config, options = fired[-1]

    [result] = HOOKS.fire_hooks(event, context, config, **options)

    assert "idempotent skip" in result.detail
    assert len(_stamps(world, number, f"#{number} moved to review")) == 1


def test_a_move_reads_the_comments_once(world: World) -> None:
    number = _started(world)
    before = _reads(world, number, "comments")

    assert world.move(number, "review") == 0

    assert _reads(world, number, "comments") == before + 1


# --- a close made again ---------------------------------------------------------


def test_a_close_after_a_reopen_posts_again(
    world: World, ro: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    number = world.file_issue()
    assert world.promote(number) == 0
    assert world.close(number, "--reason", WONT_DO) == 0
    assert _reopen(ro, number, monkeypatch) == 0

    assert world.close(number, "--reason", WONT_DO) == 0

    stamps = _stamps(world, number, f"#{number} closed")
    assert len(stamps) == 2
    assert stamps[0] != stamps[1]


def test_a_rerun_of_the_same_close_posts_nothing_new(world: World) -> None:
    """`done-work`'s close after a merge, run again — from another clone, or to
    finish a run that stopped later on — fires the hook again for that close.
    The close time comes with the issue's first read, at no read of its own."""
    number = _merged(world)

    assert world.close(number, "--mode", "pr-merge") == 0
    assert world.close(number, "--mode", "pr-merge") == 0

    assert len(_stamps(world, number, f"#{number} closed")) == 1
    assert _reads(world, number, "closedAt") == 0


def test_a_close_the_run_makes_reads_its_time_once(world: World) -> None:
    number = world.file_issue()
    assert world.promote(number) == 0

    assert world.close(number, "--reason", WONT_DO) == 0

    assert len(_stamps(world, number, f"#{number} closed")) == 1
    assert _reads(world, number, "closedAt") == 1


# --- comments that cannot be read -----------------------------------------------


def test_comments_that_cannot_be_read_post_and_warn(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    """A hook comment is the adopter's notice, not the audit record: posting it
    without the check, and saying so, beats dropping it unseen."""
    number = _started(world)
    world.tracker.comment_reads_fail.add(number)
    capsys.readouterr()

    assert world.move(number, "review") == 0

    assert len(_stamps(world, number, f"#{number} moved to review")) == 1
    assert (
        f"[warn] #0 post-comment: could not read the comments on #{number}"
        in capsys.readouterr().err
    )
