"""Pools of workers across the open Milestones (DEC-061, ADR-072 points 2, 3 and 6).

[project-management:DEC-061-pools-of-workers] lets a project's topology declare
pools of workers, and each seat that builds names the pools it serves
(``_lib/topology``). A Milestone joins a pool by its ``Pool:`` line, which
``_lib/milestone`` alone reads (:func:`milestone.milestone_pool`). This module
joins the two for the commands that need both. The module that reads the
topology reads no Milestone, and the reckoning of ready work
(``_lib/task_pool``) reads no GitHub ([pkit:ADR-072] points 1 and 2).

- :func:`map_pools` maps the open Milestones, as one listing returns them, to
  their pools, and :func:`read_map` makes that one read. A command reads the
  open Milestones once in its run, and only where the topology declares pools.
- :meth:`PoolMap.numbers` gives a seat's set of Milestone numbers, which the
  command that takes the next Task hands to the reckoning (ADR-072 point 2).
  :func:`why_none_ready` says why nothing is ready, in terms of the seat's pools.
- :func:`listing_warnings` names what would leave work stranded, for the
  listing of seats and taking a seat (DEC-061 point 10).
- :func:`check_take` is the take's own check of a Task's pool: a warning,
  never a gate (DEC-061 point 5).
- :func:`move` judges a write of a Task's Milestone: whether it brings the Task
  into a pool or moves it between pools, which asks the person
  (:func:`authorise`), or takes it out of one, which asks nothing (DEC-061
  point 6). The pools are read only where a Milestone of the move carries a
  ``Pool:`` line, so a project with no pools reads nothing more. Where they
  cannot be read, the write asks, so no Task enters a pool unasked.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import consent, milestone, topology

#: The open Milestones, as one listing returns them, and a runner of `gh`.
Rows = list[dict[str, Any]]
Gh = Callable[[list[str]], Any]


@dataclass(frozen=True)
class PooledMilestone:
    """An open Milestone, by GitHub's number and its title, and its pool."""

    number: int
    title: str
    pool: milestone.Pool

    def label(self) -> str:
        return f"#{self.number} {topology.shown(self.title)}".rstrip()


@dataclass(frozen=True)
class PoolMap:
    """The open Milestones of one read, each with its pool, against the pools
    the topology declares."""

    declared: tuple[str, ...]
    milestones: tuple[PooledMilestone, ...] = ()

    def of(self, pool: str) -> tuple[PooledMilestone, ...]:
        """The open Milestones of ``pool``, in GitHub's number order."""
        return tuple(m for m in self.milestones if m.pool.name == pool)

    def numbers(self, pools: Iterable[str] | None) -> frozenset[int]:
        """The numbers of the open Milestones of ``pools``: a seat's set. Empty
        where the seat names no pool (DEC-061 point 8)."""
        wanted = set(pools or ())
        return frozenset(m.number for m in self.milestones if m.pool.name in wanted)

    def pool_of(self, number: int | None) -> str | None:
        """The pool of the open Milestone ``number``, or None where it is in
        none, closed, or no Milestone at all (DEC-061 point 4)."""
        found = next((m for m in self.milestones if m.number == number), None)
        return found.pool.name if found is not None else None

    def empty(self) -> list[str]:
        """The declared pools with no open Milestone."""
        return [name for name in self.declared if not self.of(name)]

    def warnings(self) -> list[str]:
        """Each open Milestone whose ``Pool:`` lines put it in no pool, with why."""
        return [w for w in (m.pool.warning(m.number) for m in self.milestones) if w]


def map_pools(rows: Iterable[Any], declared: Iterable[str]) -> PoolMap:
    """The open Milestones ``rows``, as the listing returns them, each mapped to
    its pool by :func:`milestone.milestone_pool`. Reads nothing."""
    names = tuple(declared)
    found = [
        PooledMilestone(
            row["number"],
            str(row.get("title") or ""),
            milestone.milestone_pool(str(row.get("description") or ""), names),
        )
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("number"), int)
    ]
    return PoolMap(names, tuple(sorted(found, key=lambda m: m.number)))


def read_map(
    declared: Iterable[str], *, config: dict[str, Any] | None = None, gh: Gh | None = None
) -> PoolMap | None:
    """The open Milestones, read once, mapped to their pools; None where they
    cannot be read, and a reader then takes nothing (DEC-061 point 8)."""
    rows = milestone.list_open_milestones(config or {}, gh=gh)
    if rows is None:
        return None
    return map_pools(rows, declared)


# ---- taking work (DEC-061 points 5 and 8) ------------------------------------------


def why_none_ready(seat_pools: Iterable[str] | None, pool_map: PoolMap) -> str:
    """Why no Task is ready for a seat, in terms of its pools (DEC-061 point 8)."""
    pools = list(seat_pools or ())
    if not pools:
        return "this seat names no pool, so it takes no work of its own choosing (DEC-061 point 8)"
    empty = [name for name in pools if not pool_map.of(name)]
    held = [
        f"pool {name}: " + ", ".join(m.label() for m in pool_map.of(name))
        for name in pools
        if pool_map.of(name)
    ]
    said = [f"pool {name} has no open milestone" for name in empty]
    if held:
        said.append("no Task is ready in the open milestones of " + "; ".join(held))
    return ", and ".join(said)


def builds(seat: Any) -> bool:
    """Whether ``seat``, as a clone holds it, builds: a worker's or a lead's."""
    return seat is not None and getattr(seat, "role", None) in topology.BUILDERS


def check_take(issue: Mapping[str, Any], clone: Any, config: dict[str, Any]) -> list[str]:
    """The take's own check of a Task's pool (DEC-061 point 5): a warning where
    the Task's native Milestone is in no pool the seat serves, or where its pool
    cannot be read. A take as directed goes on, so it is never a gate. Empty
    where the topology declares no pool, or the clone's seat builds nothing."""
    if getattr(clone, "pools", None) is None or not builds(getattr(clone, "seat", None)):
        return []
    seat_pools = tuple(clone.seat.pools or ())
    number = native_number(issue)
    pool_map = read_map(clone.pools, config=config) if number is not None else None
    if number is not None and pool_map is None:
        return [
            f"the pool of its Milestone #{number} could not be read, so whether this seat's "
            "pools hold it cannot be told (DEC-061 point 5)."
        ]
    pool = pool_map.pool_of(number) if pool_map is not None else None
    if pool is not None and pool in seat_pools:
        return []
    where = f"the pool {pool}" if pool is not None else "no pool"
    served = ", ".join(seat_pools) or "none"
    return [
        f"it is in {where}, outside the pools this seat serves ({served}), so it is taken as "
        "directed, and no seat would choose it of its own (DEC-061 point 5)."
    ]


def native_number(issue: Mapping[str, Any]) -> int | None:
    """The number of an issue's native Milestone, never its body's `Milestone:`
    line (DEC-061 point 4)."""
    native = issue.get("milestone")
    number = native.get("number") if isinstance(native, dict) else None
    return number if isinstance(number, int) and not isinstance(number, bool) else None


# ---- the listings (DEC-061 point 10) ------------------------------------------------


def listing_warnings(tree: topology.Topology, pool_map: PoolMap | None) -> list[str]:
    """What would leave work stranded: a pool no seat serves, a seat that builds
    and names no pool, a pool with no open Milestone, and each Milestone whose
    ``Pool:`` lines put it in no pool, an undeclared pool among them. Where the
    Milestones could not be read, only what the topology shows."""
    found = topology.stranded(tree)
    if pool_map is not None:
        found += [f"the pool {name} has no open milestone." for name in pool_map.empty()]
        found += pool_map.warnings()
    return found


def show_pools(pool_map: PoolMap, out: Any = None) -> None:
    """Print each declared pool's open Milestones, by GitHub's number and title."""
    stream = out if out is not None else sys.stdout
    print("\nPools of workers and their open milestones (DEC-061 point 10):", file=stream)
    for name in pool_map.declared:
        held = pool_map.of(name)
        listed = ", ".join(m.label() for m in held) if held else "no open milestone"
        print(f"  {name}: {listed}", file=stream)


# ---- writes of a Task's Milestone (DEC-061 point 6) --------------------------------


@dataclass(frozen=True)
class Move:
    """What a write of a Task's Milestone does to its pool. ``asks`` where it
    brings the Task into a pool or moves it between pools. ``note`` says why the
    pools could not be told, where they could not, and the write then asks."""

    asks: bool
    before: str | None = None
    after: str | None = None
    note: str | None = None

    def said(self) -> str:
        """The change, in words a plan line or an audit comment carries."""
        return f"pool {self.before or 'none'} → {self.after or 'none'}"

    def logged(self) -> str:
        """The record of the person's consent, for the Task's audit comment."""
        return f"{self.said()}, with the person's consent (DEC-061 point 6)"


def declared_pools(capability_root: Path) -> tuple[tuple[str, ...] | None, str | None]:
    """The pools the default branch's topology declares, or None where it
    declares none; with a note where the topology cannot be read in full."""
    try:
        tree = topology.read(capability_root)
    except topology.Unresolved as exc:
        return None, f"the topology could not be read from the default branch ({exc})"
    if tree is None:
        return None, None
    if tree.not_understood:
        return None, "this code cannot read the topology of the default branch in full"
    return tree.pools, None


def move(
    before: int | None,
    after: int | None,
    *,
    rows: Rows | None,
    capability_root: Path,
) -> Move:
    """Judge a write that moves a Task from the Milestone ``before`` to
    ``after``, each by GitHub's number or None, against ``rows``, the open
    Milestones one listing returned, None where they could not be read.

    Leaving a pool asks nothing (DEC-061 point 6). The topology is read only
    where a Milestone of the move carries a well-formed ``Pool:`` line. Where
    the Milestones or the topology cannot be read, a line's pool is taken to
    stand, so the write asks rather than let a Task enter a pool unasked."""
    if after is None:
        return Move(False)
    if rows is None:
        return Move(True, note="the open milestones could not be read")
    descriptions = {
        row["number"]: str(row.get("description") or "")
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("number"), int)
    }
    lines = {n: milestone.parse_pool_line(descriptions.get(n, "")) for n in (before, after) if n}
    if after not in descriptions or lines[after].name is None:
        return Move(False)
    declared, note = declared_pools(capability_root)
    if note is not None:
        named = {line.name for line in lines.values() if line.name is not None}
        declared = tuple(sorted(named))
    pools = {n: milestone.milestone_pool(descriptions.get(n, ""), declared).name for n in lines}
    was = pools.get(before) if before is not None else None
    now = pools[after]
    return Move(now is not None and now != was, was, now, note)


def authorise(found: Move, *, subject: str, yes: bool, verb: str) -> int | None:
    """Ask the person where ``found`` brings a Task into a pool or moves it
    between pools (DEC-061 point 6): at a terminal, or by ``--yes`` given on
    their word. Off a terminal without it, the write is refused. Returns None
    to go on, else the exit code to stop with. ``subject`` names the Task."""
    if not found.asks:
        return None
    if found.note is not None:
        print(f"[note] {verb}: {found.note}, so the write asks.", file=sys.stderr)
    return consent.authorise(
        f"Put {subject} into the pool {found.after} ({found.said()})? [y/N] ",
        yes=yes,
        step=f"Putting {subject} into the pool {found.after}",
        verb=verb,
    )
