"""The shared pool of work and its ready Tasks — `_lib/task_pool` (DEC-059 point 7).

A ready Task is an open Task in Backlog with no owner whose `## Dependencies`
section names no open issue (DEC-005), or, in a project with a topology, a Task
In Progress whose claim no longer counts (DEC-059 point 9). The pool ranks them
by priority (DEC-012), within the scope of the seat this clone holds. The
listing's rows are built here, and the owners come from the in-memory GitHub
(`tests/pm_ownership_support.FakeGitHub`).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from tests.pm_ownership_support import FakeGitHub, clone_with, topology_with

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAP_ROOT / "scripts"


@pytest.fixture(scope="module")
def tp():
    sys.path.insert(0, str(SCRIPTS))
    try:
        yield importlib.import_module("_lib.task_pool")
    finally:
        sys.path.remove(str(SCRIPTS))


@pytest.fixture(scope="module")
def readers(tp):
    """The shipped schemas, as the pool reads a Task's type and axes."""
    yaml = YAML(typ="safe")
    return tp.Readers(
        issue_types=yaml.load((CAP_ROOT / "schemas" / "issue-types.yaml").read_text()),
        classification=yaml.load((CAP_ROOT / "schemas" / "classification.yaml").read_text()),
    )


def _row(
    number: int,
    *,
    title: str = "[Task] do the thing",
    state_label: str = "state:backlog",
    priority: str | None = "Medium",
    kind: str = "feature",
    workstream: str = "cli",
    assignees: tuple[str, ...] = (),
    body: str = "Feature: #1\n\n## What\n\nx\n",
    state: str = "OPEN",
) -> dict[str, Any]:
    labels = [state_label, f"type:{kind}", f"workstream:{workstream}"]
    if priority is not None:
        labels.append(f"priority:{priority}")
    return {
        "number": number,
        "title": title,
        "labels": [{"name": n} for n in labels],
        "assignees": [{"login": a} for a in assignees],
        "milestone": None,
        "state": state,
        "body": body,
    }


def _ready(tp, readers, rows, *, open_numbers=(), scope=None, takes_over=False) -> list[int]:
    found = tp.candidates(
        rows,
        open_numbers=open_numbers or [r["number"] for r in rows],
        login="me",
        scope=scope,
        takes_over=takes_over,
        readers=readers,
    )
    return [c.number for c in found]


def _scope(workstreams: tuple[str, ...] = (), types: tuple[str, ...] = ()) -> Any:
    return importlib.import_module("_lib.topology").Scope(workstreams, types)


# ---- dependencies (DEC-005) ------------------------------------------------------


def test_dependencies_are_the_references_the_section_names(tp) -> None:
    body = (
        "Feature: #1\n\n## What\n\nSee #5.\n\n## Dependencies\n\n"
        "- #12 lands first, then #13\n- and #12 again\n\n### Notes\n\nalso #14\n\n"
        "## Doc impact\n\n- #15 is not a dependency\n"
    )
    assert tp.dependencies(body) == (12, 13, 14)


def test_dependencies_ignore_what_is_not_a_reference_to_this_repository(tp) -> None:
    body = (
        "## Dependencies\n\n"
        "<!-- e.g. Blocked by: #90 -->\n"
        "- other/repo#91 and `#92` and &#93;\n"
        "- https://github.com/o/r/issues/94\n"
        "```\n#95\n```\n"
        "- this Task, #42, and #96\n"
    )
    assert tp.dependencies(body, own=42) == (96,)


def test_dependencies_leave_out_the_provenance_footer(tp) -> None:
    body = "## Dependencies\n\n- #7\n\n<!-- pkit-provenance:start -->\n\n---\n#8\n"
    assert tp.dependencies(body) == (7,)


def test_a_body_with_no_dependencies_section_names_none(tp) -> None:
    assert tp.dependencies("## What\n\n#3 and #4\n") == ()
    assert tp.dependencies("") == ()


# ---- the listing ------------------------------------------------------------------


def test_an_open_backlog_task_is_ready(tp, readers) -> None:
    assert _ready(tp, readers, [_row(10)]) == [10]


def test_a_task_waiting_on_an_open_issue_is_held_back(tp, readers) -> None:
    body = "Feature: #1\n\n## Dependencies\n\n- #20\n"
    rows = [_row(10, body=body)]
    assert _ready(tp, readers, rows, open_numbers=[10, 20]) == []
    # #20 is closed, a pull request or not there: it holds nothing back.
    assert _ready(tp, readers, rows, open_numbers=[10]) == [10]


@pytest.mark.parametrize(
    "row",
    [
        pytest.param({"state_label": "state:todo"}, id="todo"),
        pytest.param({"state_label": "state:review"}, id="review"),
        pytest.param({"state": "CLOSED"}, id="closed"),
        pytest.param({"title": "[Feature] a container"}, id="feature"),
        pytest.param({"assignees": ("alice",)}, id="another-account"),
    ],
)
def test_what_is_no_ready_task(tp, readers, row: dict[str, Any]) -> None:
    assert _ready(tp, readers, [_row(10, **row)]) == []


def test_a_task_assigned_to_this_clones_account_is_ready(tp, readers) -> None:
    assert _ready(tp, readers, [_row(10, assignees=("me",))]) == [10]


def test_a_task_in_progress_is_kept_only_where_the_clone_takes_over(tp, readers) -> None:
    rows = [_row(10, state_label="state:in-progress")]
    assert _ready(tp, readers, rows) == []
    assert _ready(tp, readers, rows, takes_over=True) == [10]


def test_the_highest_in_priority_first_then_the_lowest_number(tp, readers) -> None:
    rows = [
        _row(1, priority=None),
        _row(2, priority="Low"),
        _row(5, priority="Medium"),
        _row(3, priority="Medium"),
        _row(9, priority="High"),
    ]
    assert _ready(tp, readers, rows) == [9, 3, 5, 2, 1]


def test_a_candidate_names_itself(tp, readers) -> None:
    (candidate,) = tp.candidates(
        [_row(10, priority="High")],
        open_numbers=[10],
        login="me",
        scope=None,
        takes_over=False,
        readers=readers,
    )
    assert candidate.describe() == "#10 [Task] do the thing (priority High, in Backlog)"
    assert (candidate.kind, candidate.workstream) == ("feature", "cli")


def test_the_type_falls_back_to_the_titles_prefix(tp, readers) -> None:
    row = _row(10, title="[Test] cover it")
    row["labels"] = [lbl for lbl in row["labels"] if not lbl["name"].startswith("type:")]
    assert _ready(tp, readers, [row], scope=_scope(types=("test",))) == [10]


# ---- the scope (DEC-059 point 7) ---------------------------------------------------


def test_a_scope_takes_what_matches_each_part_it_names(tp, readers) -> None:
    rows = [
        _row(1, kind="test", workstream="cli"),
        _row(2, kind="test", workstream="docs"),
        _row(3, kind="feature", workstream="cli"),
    ]
    assert _ready(tp, readers, rows, scope=_scope(types=("test",))) == [1, 2]
    assert _ready(tp, readers, rows, scope=_scope(workstreams=("cli",))) == [1, 3]
    assert _ready(tp, readers, rows, scope=_scope(("cli",), ("test",))) == [1]
    assert _ready(tp, readers, rows) == [1, 2, 3]


def test_no_scope_takes_every_task(tp) -> None:
    assert tp.in_scope(None, None, None)
    assert not tp.in_scope(None, None, _scope(types=("test",)))


# ---- the owner (DEC-035 point 6, DEC-059 point 9) -----------------------------------


def _owner(tp, comments: list[dict], holders: dict | None = None):
    return tp.ownership.resolve_owner(
        comments=comments, labels=[], assignee_login="me", holders=holders
    )


def _stamp(tp, instance: int, seat: str | None = None, key: str | None = None) -> dict:
    body = tp.ownership.format_event_comment(
        event="claim",
        instance=instance,
        seat=seat,
        seat_number=instance if seat else None,
        clone=key,
    )
    return {"author": {"login": "me"}, "body": body}


def test_a_backlog_task_is_free_when_no_other_instance_holds_it(tp) -> None:
    assert tp.free_for(_owner(tp, []), 2, tp.BACKLOG)
    assert tp.free_for(_owner(tp, [_stamp(tp, 2)]), 2, tp.BACKLOG)
    assert not tp.free_for(_owner(tp, [_stamp(tp, 3)]), 2, tp.BACKLOG)
    assert not tp.free_for(_owner(tp, [_stamp(tp, 2), _stamp(tp, 1)]), 2, tp.BACKLOG)


def test_a_task_whose_seat_was_released_returns_to_the_pool(tp) -> None:
    """DEC-059 points 5 and 9: judged when read, with no write to the issue."""
    held = tp.ownership.Holder(tp.ownership.SEAT_HELD, "me", "k1")
    free = tp.ownership.Holder(tp.ownership.SEAT_FREE)
    unread = tp.ownership.Holder(tp.ownership.SEAT_UNREAD)
    claim = [_stamp(tp, 1, "worker-1", "k1")]
    assert tp.free_for(_owner(tp, claim, {"worker-1": free}), 2, tp.IN_PROGRESS)
    assert tp.free_for(_owner(tp, claim, {"worker-1": free}), 2, tp.BACKLOG)
    assert not tp.free_for(_owner(tp, claim, {"worker-1": held}), 2, tp.IN_PROGRESS)
    assert not tp.free_for(_owner(tp, claim, {"worker-1": unread}), 2, tp.IN_PROGRESS)


def test_a_task_in_progress_that_no_claim_was_made_on_is_nobodys(tp) -> None:
    assert not tp.free_for(_owner(tp, [], {}), 2, tp.IN_PROGRESS)


def test_taken_by_another_reads_the_lowest_claim(tp) -> None:
    assert tp.taken_by_another(_owner(tp, [_stamp(tp, 3)]), 2)
    assert tp.taken_by_another(_owner(tp, [_stamp(tp, 1), _stamp(tp, 2)]), 2)
    assert not tp.taken_by_another(_owner(tp, [_stamp(tp, 2), _stamp(tp, 3)]), 2)
    assert not tp.taken_by_another(_owner(tp, []), 2)
    assert not tp.taken_by_another(None, 2)


# ---- who takes ----------------------------------------------------------------------


def _claims(tp):
    return tp.instance_claims


def test_outside_a_topology_a_clone_takes_with_no_scope(tp, tmp_path, monkeypatch) -> None:
    ic = _claims(tp)
    clone_with(ic, monkeypatch, None)
    assert tp.taker(tmp_path, "me", {}) == tp.Taker(None)
    clone_with(ic, monkeypatch, 2)
    taker = tp.taker(tmp_path, "me", {})
    assert taker.clone is not None and taker.clone.instance == 2
    assert (taker.scope, taker.refusal, taker.takes_over) == (None, None, False)


def test_a_seat_gives_its_scope(tp, tmp_path, monkeypatch) -> None:
    ic = _claims(tp)
    scope = _scope(types=("test",))
    holders = {"tester": ic.ownership.Holder(ic.ownership.SEAT_HELD, "me", "k2")}
    seat = ic.Seat("tester", 2, ic.WORKER, scope)
    topology_with(ic, monkeypatch, ic.Topology(seat, holders), key="k2")
    taker = tp.taker(tmp_path, "me", {})
    assert taker.refusal is None
    assert taker.scope is scope
    assert taker.takes_over


def test_a_planners_seat_takes_nothing(tp, tmp_path, monkeypatch) -> None:
    ic = _claims(tp)
    topology_with(ic, monkeypatch, ic.Topology(ic.Seat("planner", 1, ic.PLANNER), {}), key="k1")
    refusal = tp.taker(tmp_path, "me", {}).refusal
    assert refusal is not None and "builds none of it (DEC-059 point 2)" in refusal


def test_a_lead_takes_within_its_scope(tp, tmp_path, monkeypatch) -> None:
    ic = _claims(tp)
    scope = _scope(workstreams=("cli",))
    topology_with(ic, monkeypatch, ic.Topology(ic.Seat("lead", 1, ic.LEAD, scope), {}), key="k1")
    taker = tp.taker(tmp_path, "me", {})
    assert (taker.refusal, taker.scope) == (None, scope)


def test_a_clone_that_holds_no_seat_of_a_topology_takes_nothing(tp, tmp_path, monkeypatch) -> None:
    ic = _claims(tp)
    clone_with(ic, monkeypatch, 7)
    topology_with(ic, monkeypatch, ic.Topology(None, {}), key="k9")
    refusal = tp.taker(tmp_path, "me", {}).refusal
    assert refusal is not None and refusal.startswith("this clone holds no seat")


def test_the_pool_reads_its_owners_through_the_one_fold(tp, tmp_path) -> None:
    """`read_owner` folds as the guard does, so the pool and the guard agree."""
    ic = _claims(tp)
    gh = FakeGitHub()
    gh.add(10)
    gh.post(10, _stamp(tp, 3)["body"])
    resolution = ic.read_owner(10, ic.Clone(2, "comment", "me", tmp_path), {}, run=gh)
    assert resolution is not None
    assert not tp.free_for(resolution, 2, tp.BACKLOG)
    assert tp.taken_by_another(resolution, 2)
