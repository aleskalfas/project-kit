"""Pools of workers across the open Milestones — `_lib/pools` (DEC-061, ADR-072).

The module maps the open Milestones of one read to their pools, gives a seat's
set of Milestone numbers, says why nothing is ready, names what would leave
work stranded, and judges a write of a Task's Milestone: whether it asks the
person. These tests run with no GitHub: the open Milestones are rows a listing
would return, and the topology's pools are given or stubbed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import pools, topology  # noqa: E402

ROWS = [
    {"number": 4, "title": "Sprint 4: docs", "description": "Pool: bravo"},
    {"number": 3, "title": "Sprint 3: auth", "description": "Close trigger: either\nPool: alpha"},
    {"number": 5, "title": "Sprint 5: misc", "description": "Close trigger: either"},
    {"number": 6, "title": "Sprint 6: odd", "description": "Pool: charlie"},
    {"number": 7, "title": "Sprint 7: twice", "description": "Pool: alpha\nPool: bravo"},
]


def _map(declared: tuple[str, ...] = ("alpha", "bravo", "delta")) -> pools.PoolMap:
    return pools.map_pools(ROWS, declared)


def test_each_open_milestone_is_mapped_to_its_pool() -> None:
    pool_map = _map()
    assert [m.number for m in pool_map.milestones] == [3, 4, 5, 6, 7]
    assert [m.number for m in pool_map.of("alpha")] == [3]
    assert pool_map.pool_of(4) == "bravo"
    assert pool_map.pool_of(5) is None and pool_map.pool_of(99) is None
    assert pool_map.pool_of(None) is None
    assert pool_map.empty() == ["delta"]
    warnings = pool_map.warnings()
    assert len(warnings) == 2
    assert "milestone #6 names the pool 'charlie'" in warnings[0]
    assert "milestone #7 has more than one `Pool:` line" in warnings[1]


def test_a_seats_set_is_the_open_milestones_of_its_pools() -> None:
    pool_map = _map()
    assert pool_map.numbers(("alpha", "bravo")) == {3, 4}
    assert pool_map.numbers(()) == frozenset()
    assert pool_map.numbers(None) == frozenset()


def test_why_none_ready_speaks_of_the_seats_pools() -> None:
    pool_map = _map()
    assert "this seat names no pool" in pools.why_none_ready((), pool_map)
    said = pools.why_none_ready(("delta", "alpha"), pool_map)
    assert "pool delta has no open milestone" in said
    assert "no Task is ready in the open milestones of pool alpha: #3 Sprint 3: auth" in said


def test_the_listing_warns_of_stranded_work() -> None:
    tree = topology.parse(
        {
            "schema_version": 1,
            "pools": ["alpha", "bravo", "delta"],
            "seats": [
                {"name": "w1", "role": "worker", "pools": ["alpha"], "state_issue": 1},
                {"name": "w2", "role": "lead", "state_issue": 2},
            ],
        }
    )
    found = pools.listing_warnings(tree, _map())
    joined = "\n".join(found)
    assert "the pool bravo is served by no seat" in joined
    assert "the seat w2, a lead, names no pool" in joined
    assert "the pool delta has no open milestone" in joined
    assert "milestone #6 names the pool 'charlie'" in joined
    assert pools.listing_warnings(tree, None) == topology.stranded(tree)


# ---- the take's own check (DEC-061 point 5) --------------------------------------------


def _clone(role: str = "worker", seat_pools: tuple[str, ...] | None = ("alpha",), declared=()):
    seat = SimpleNamespace(role=role, pools=seat_pools)
    return SimpleNamespace(seat=seat, pools=declared)


def test_the_take_s_own_check_warns_of_a_task_outside_the_seats_pools(monkeypatch) -> None:
    monkeypatch.setattr(pools.milestone, "list_open_milestones", lambda _c, gh=None: ROWS)
    clone = _clone(declared=("alpha", "bravo"))
    assert pools.check_take({"milestone": {"number": 3}}, clone, {}) == []
    (outside,) = pools.check_take({"milestone": {"number": 4}}, clone, {})
    assert "the pool bravo, outside the pools this seat serves (alpha)" in outside
    (none,) = pools.check_take({"milestone": None}, clone, {})
    assert "it is in no pool" in none


def test_the_take_s_own_check_reads_nothing_without_pools_or_for_a_planner(monkeypatch) -> None:
    def fail(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("no milestone is read")

    monkeypatch.setattr(pools.milestone, "list_open_milestones", fail)
    assert pools.check_take({"milestone": {"number": 4}}, _clone(declared=None), {}) == []
    planner = _clone(role="planner", declared=("alpha",))
    assert pools.check_take({"milestone": {"number": 4}}, planner, {}) == []


# ---- writes of a Task's Milestone (DEC-061 point 6) -------------------------------------


@pytest.fixture
def declared(monkeypatch: pytest.MonkeyPatch):
    """Returns `set(pools, note=None)`: what the topology declares, as read; the
    list returned counts the reads."""
    reads: list[int] = []

    def set_declared(found: tuple[str, ...] | None, note: str | None = None) -> list[int]:
        def read(_root: Path) -> Any:
            reads.append(1)
            return found, note

        monkeypatch.setattr(pools, "declared_pools", read)
        return reads

    return set_declared


@pytest.mark.parametrize(
    ("before", "after", "said"),
    [
        (None, 3, "pool none → alpha"),
        (5, 3, "pool none → alpha"),
        (4, 3, "pool bravo → alpha"),
        (3, 4, "pool alpha → bravo"),
        (6, 3, "pool none → alpha"),
    ],
)
def test_a_write_asks_where_it_brings_a_task_into_a_pool_or_between_pools(
    declared, before, after, said
) -> None:
    declared(("alpha", "bravo"))
    found = pools.move(before, after, rows=ROWS, capability_root=Path("."))
    assert found.asks and found.said() == said


@pytest.mark.parametrize(("before", "after"), [(3, 3), (3, 5), (3, None), (3, 6), (None, 7)])
def test_a_write_within_one_pool_or_out_of_a_pool_asks_nothing(declared, before, after) -> None:
    declared(("alpha", "bravo"))
    assert not pools.move(before, after, rows=ROWS, capability_root=Path(".")).asks


def test_a_write_between_milestones_with_no_pool_line_reads_no_topology(declared) -> None:
    reads = declared(("alpha",))
    assert pools.move(None, 5, rows=ROWS, capability_root=Path(".")) == pools.Move(False)
    assert pools.move(3, 5, rows=ROWS, capability_root=Path(".")) == pools.Move(False)
    assert reads == []


def test_without_pools_declared_no_write_asks(declared) -> None:
    declared(None)
    assert not pools.move(None, 3, rows=ROWS, capability_root=Path(".")).asks


def test_where_the_pools_cannot_be_told_the_write_asks(declared) -> None:
    declared(None, "the topology could not be read")
    found = pools.move(None, 6, rows=ROWS, capability_root=Path("."))
    assert (found.asks, found.after, found.note) == (
        True,
        "charlie",
        "the topology could not be read",
    )
    unread = pools.move(None, 3, rows=None, capability_root=Path("."))
    assert unread.asks and unread.note == "the open milestones could not be read"


def test_the_person_is_asked_and_off_a_terminal_the_write_is_refused(monkeypatch, capsys) -> None:
    found = pools.Move(True, None, "alpha")
    assert pools.authorise(pools.Move(False), subject="#9", yes=False, verb="edit-issue") is None
    assert pools.authorise(found, subject="#9", yes=True, verb="edit-issue") is None
    monkeypatch.setattr(pools.consent, "at_a_terminal", lambda: False)
    assert pools.authorise(found, subject="#9", yes=False, verb="edit-issue") == 1
    assert "Putting #9 into the pool alpha is the person's to authorise" in capsys.readouterr().err
    monkeypatch.setattr(pools.consent, "at_a_terminal", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    assert pools.authorise(found, subject="#9", yes=False, verb="edit-issue") is None
    assert found.logged() == "pool none → alpha, with the person's consent (DEC-061 point 6)"


def test_declared_pools_fail_closed_on_a_topology_this_code_cannot_read(monkeypatch) -> None:
    monkeypatch.setattr(
        pools.topology, "read", lambda _r: topology.parse({"schema_version": 2, "seats": []})
    )
    found, note = pools.declared_pools(Path("."))
    assert found is None and note is not None and "in full" in note
    monkeypatch.setattr(
        pools.topology,
        "read",
        lambda _r: topology.parse({"schema_version": 1, "pools": ["alpha"], "seats": []}),
    )
    assert pools.declared_pools(Path(".")) == (("alpha",), None)

    def unresolved(_r: Path) -> Any:
        raise topology.Unresolved("no default branch")

    monkeypatch.setattr(pools.topology, "read", unresolved)
    found, note = pools.declared_pools(Path("."))
    assert found is None and note is not None and "no default branch" in note
