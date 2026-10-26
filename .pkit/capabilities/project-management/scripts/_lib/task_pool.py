"""The shared pool of work, and which Task in it is taken next (DEC-059 point 7).

[project-management:DEC-059-topology-of-seats] point 7 has a worker take the next
ready Task from one pool that every seat shares, the highest in priority first
([project-management:DEC-012-classification-axes]). A ready Task is one of two
kinds:

- an open Task in Backlog, with no owner, whose dependencies name no open issue
  ([project-management:DEC-005-linking-and-containment])
- in a project with a topology, a Task In Progress whose claim no longer counts,
  since its seat was released (point 9). Lapse is not built yet.

Readiness is reckoned here once ([project-management:DEC-025-parallelization-primitive]),
and ``next-task`` takes the first ready Task through ``start-work``. Two halves:

- :func:`candidates` reads the open issues of work that the one read of issues
  returns (``_lib/issue_list``), and reads no more of GitHub. It keeps the open
  Tasks in Backlog, and those In Progress where the clone may take one over, that
  are not assigned to another account, fall in the seat's scope and name no open
  issue among their dependencies. It ranks them by priority, then by number.
- :func:`in_pool` and :func:`owned_by` judge one candidate by its owner, as the
  ownership seam folds it (``_lib/instance_claims.read_owner``). A Task in Backlog
  with an owner is not in the pool, as point 7 says.

This clone's own Tasks come first
---------------------------------
A lead owns what it files (point 7), and the clash guard refuses that Task to
every other clone. A Task in Backlog that this clone's instance owns is its own
work, outside the pool, and :func:`ordered` puts it before every pool Task. Its
own Tasks rank by priority, then by number, among themselves. A clone claims only
a Task its account is assigned to, so only such a Task in Backlog may be its own
(:func:`may_be_own`), and only these owners are read before the first start.

Dependencies are prose
----------------------
DEC-005 keeps dependencies as prose, in an optional ``## Dependencies`` section,
and the typed ``Blocked by:`` line DEC-025 names is not built. :func:`dependencies`
reads each ``#N`` the section names. It ignores what an HTML comment, a fenced
code block or an inline code span holds, a reference to another repository's issue
(``owner/repo#N``), an issue named only by its URL, and the Task itself. The pool
is the repository's own (DEC-059, Implications), and DEC-025's open question 8
leaves another repository's issues to a later record. A number that is no open
issue, since it is closed, a pull request or not there, holds nothing back.

The scope
---------
A seat's scope (``_lib/topology.Scope``) narrows the pool of its own seat, and
reserves nothing for it. A Task falls in it where it matches each part the scope
names: its workstream among the scope's workstreams, and its type among the
scope's types. :func:`in_scope` takes the scope as its input, and :func:`taker`
reads it from the one place it lives, the seat this clone holds
(``instance_claims.Seat.scope``), which the run's reading of the topology fills.

The axes are read through the read seam (``axis_labels.resolve_read``), and a
Task's type falls back to its title's prefix, as ``start-work`` reads it. An axis
that a board carries is not read here, so such a Task ranks after every Task whose
priority is read, and a scope that names a part on that axis does not take it.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import (
    axis_labels,
    classification_rules,
    instance_claims,
    issue_position,
    provenance,
    topology,
)
from _lib import instance_ownership as ownership
from _lib.body_rules import lines_outside_fences
from _lib.structural_type import infer_structural_type

#: The fields of the one listing the pool reads.
LIST_FIELDS = "number,title,labels,assignees,milestone,state,body"

BACKLOG = "backlog"
IN_PROGRESS = "in-progress"

_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
#: ``#N`` where no word character, slash or ampersand comes before it: ``a/b#12``
#: names another repository's issue and ``&#12;`` is an HTML entity.
_REFERENCE = re.compile(r"(?<![\w/&])#(\d{1,9})\b")


@dataclass(frozen=True)
class Candidate:
    """One open Task the pool may hand out, read from the listing."""

    number: int
    title: str
    state: str
    priority: str | None
    workstream: str | None
    kind: str | None
    rank: int
    #: Whether the Task is assigned to this clone's account.
    assigned: bool = False

    def describe(self, *, own: bool = False) -> str:
        """How a line names the Task: its number, title, priority and state, and
        whether it is this clone's own."""
        where = (
            "in Backlog" if self.state == BACKLOG else "In Progress, its claim no longer counting"
        )
        if own:
            where += ", this clone's own"
        return f"#{self.number} {self.title} (priority {self.priority or 'not read'}, {where})"


@dataclass(frozen=True)
class Readers:
    """The capability's schemas, as the pool reads a Task's type and axes."""

    issue_types: Mapping[str, Any]
    classification: Mapping[str, Any]
    substrate_map: axis_labels.SubstrateMap | None = None


@dataclass(frozen=True)
class Taker:
    """Who takes from the pool: this clone where it takes part in instance
    ownership, the scope of its seat, and why it may not take, where it may not."""

    clone: instance_claims.Clone | None
    scope: topology.Scope | None = None
    refusal: str | None = None

    @property
    def takes_over(self) -> bool:
        """Whether this clone may take over a Task In Progress whose claim no
        longer counts: only in a project with a topology (DEC-059 point 9)."""
        return self.clone is not None and self.clone.holders is not None


def taker(
    capability_root: Path, login: str | None, config: dict, *, dry_run: bool = False
) -> Taker:
    """This clone as a taker from the pool, and the scope of its seat.

    The topology is read once, and the clone's seat confirmed on its state issue
    (``instance_claims.read_topology``), which raises ``Unconfirmed`` where the
    seat cannot be confirmed. ``dry_run`` releases no retired seat. Outside a
    topology, a clone with an instance id, or with none, takes with no scope. In
    a project with a topology, a clone takes only from the seat it holds: one
    that holds none may not take, nor may a planner's seat, which builds none of
    the work (DEC-059 point 2)."""
    reading = instance_claims.read_topology(capability_root, config, login=login, dry_run=dry_run)
    if reading is None:
        return Taker(instance_claims.numbered_clone(capability_root, login))
    clone = instance_claims.seat_clone(reading, capability_root, login)
    if clone is None:
        return Taker(
            None,
            refusal=(
                "this clone holds no seat of the project's topology, so it takes no work "
                "from the shared pool (DEC-059 points 4 and 6). Take a seat first."
            ),
        )
    seat = clone.seat
    if seat is not None and seat.role == instance_claims.PLANNER:
        return Taker(
            clone,
            refusal=(
                f"this clone holds the planner's seat {seat.name}, which slices and files the "
                "work and builds none of it (DEC-059 point 2)."
            ),
        )
    return Taker(clone, seat_scope(seat))


def seat_scope(seat: instance_claims.Seat | None) -> topology.Scope | None:
    """The scope of the seat this clone holds, or None: the one place the pool
    reads a seat's scope (DEC-059 point 7)."""
    return None if seat is None else seat.scope


# ---- dependencies (DEC-005) ------------------------------------------------


def dependencies(body: str, *, own: int | None = None) -> tuple[int, ...]:
    """The issues the ``## Dependencies`` section of ``body`` names by ``#N``, in
    the order they first appear, with ``own``, the Task's own number, left out.

    The module docstring lists what is read and what is ignored."""
    text = _COMMENT.sub("", provenance.strip_footer(body or ""))
    numbers: list[int] = []
    inside = False
    for line in lines_outside_fences(text):
        heading = _HEADING.match(line)
        if heading is not None and len(heading.group(1)) <= 2:
            inside = len(heading.group(1)) == 2 and heading.group(2).lower() == "dependencies"
            continue
        if not inside:
            continue
        for match in _REFERENCE.finditer(_CODE_SPAN.sub("", line)):
            number = int(match.group(1))
            if number != own and number not in numbers:
                numbers.append(number)
    return tuple(numbers)


# ---- the scope (DEC-059 point 7) ---------------------------------------------


def in_scope(kind: str | None, workstream: str | None, scope: topology.Scope | None) -> bool:
    """Whether a Task of type ``kind`` in ``workstream`` falls in ``scope``: it
    matches each part the scope names. No scope takes every Task."""
    if scope is None:
        return True
    if scope.workstreams and workstream not in scope.workstreams:
        return False
    return not scope.types or kind in scope.types


# ---- the listing -------------------------------------------------------------


def candidates(
    rows: Iterable[Any],
    *,
    open_numbers: Iterable[int],
    login: str | None,
    scope: topology.Scope | None,
    takes_over: bool,
    readers: Readers,
) -> list[Candidate]:
    """The open Tasks the pool may hand out, the highest in priority first.

    ``rows`` are the open issues of work, as the listing returns them in
    :data:`LIST_FIELDS`. ``open_numbers`` are the numbers of every open issue,
    state issues among them. ``login`` is this clone's account: a Task assigned
    to another account is left out, since ``start-work`` refuses it. A Task In
    Progress is kept only where ``takes_over``. Owners are not judged here."""
    still_open = frozenset(open_numbers)
    order = _priorities(readers.classification)
    out: list[Candidate] = []
    for row in rows:
        candidate = _candidate(row, login, scope, takes_over, readers, order)
        if candidate is None:
            continue
        body = str(row.get("body") or "")
        if any(n in still_open for n in dependencies(body, own=candidate.number)):
            continue
        out.append(candidate)
    return sorted(out, key=lambda c: (c.rank, c.number))


def _candidate(
    row: Any,
    login: str | None,
    scope: topology.Scope | None,
    takes_over: bool,
    readers: Readers,
    order: Mapping[str, int],
) -> Candidate | None:
    """``row`` as a Candidate, or None where it is no Task the pool hands out."""
    if not isinstance(row, dict) or not isinstance(row.get("number"), int):
        return None
    if str(row.get("state") or "").lower() != "open":
        return None
    title = str(row.get("title") or "")
    labels = _label_names(row)
    structural = infer_structural_type(
        title,
        dict(readers.issue_types),
        classification=dict(readers.classification),
        labels=labels,
    )
    if structural != "task":
        return None
    state = issue_position.current_state(row, labels, readers.substrate_map)
    if state not in (BACKLOG, IN_PROGRESS) or (state == IN_PROGRESS and not takes_over):
        return None
    assignees = _assignees(row)
    if assignees and login not in assignees:
        return None
    kind = axis_labels.resolve_read("type", labels, readers.substrate_map)
    if kind is None:
        kind = classification_rules.kind_from_title(title, dict(readers.classification))
    workstream = axis_labels.resolve_read("workstream", labels, readers.substrate_map)
    if not in_scope(kind, workstream, scope):
        return None
    priority = axis_labels.resolve_read("priority", labels, readers.substrate_map)
    return Candidate(
        number=row["number"],
        title=title,
        state=state,
        priority=priority,
        workstream=workstream,
        kind=kind,
        rank=order.get(priority or "", len(order)),
        assigned=bool(assignees),
    )


def _priorities(classification: Mapping[str, Any]) -> dict[str, int]:
    """Each value of the priority axis and its place, the highest first, as
    ``classification.yaml`` lists them (DEC-012)."""
    axes = classification.get("axes") if isinstance(classification, Mapping) else None
    axis = axes.get("priority") if isinstance(axes, Mapping) else None
    values = axis.get("values") if isinstance(axis, Mapping) else None
    if not isinstance(values, list):
        return {}
    return {str(v): i for i, v in enumerate(values)}


def _label_names(row: Mapping[str, Any]) -> list[str]:
    return [
        str(lbl.get("name", "")) if isinstance(lbl, dict) else str(lbl)
        for lbl in (row.get("labels") or [])
    ]


def _assignees(row: Mapping[str, Any]) -> list[str]:
    return [
        str(a.get("login"))
        for a in (row.get("assignees") or [])
        if isinstance(a, dict) and a.get("login")
    ]


# ---- the owner (DEC-035 point 6, DEC-059 points 7 and 9) --------------------------


def in_pool(resolution: ownership.OwnershipResolution, state: str) -> bool:
    """Whether a Task in ``state`` is in the shared pool, by its owner as the
    ownership seam folded it (DEC-059 point 7).

    In Backlog, no claim counts or stands unjudged: the Task has no owner. In
    Progress, a claim was made and none counts or stands unjudged, so the Task
    has returned to the pool (point 9). A Task In Progress that no claim was ever
    made on is nobody's to take over."""
    claimants = resolution.claimants
    if state == BACKLOG:
        return not claimants
    return bool(resolution.judgements) and not claimants


def owned_by(resolution: ownership.OwnershipResolution, instance: int, state: str) -> bool:
    """Whether a Task in ``state`` is the own work of the clone numbered
    ``instance``: a Task in Backlog whose one claim is this clone's, and counts.

    A lead owns what it files (DEC-059 point 7), and the clash guard refuses that
    Task to every other clone, so it is this clone's own, outside the pool."""
    return state == BACKLOG and resolution.claimants == {instance} and instance in resolution.owners


def may_be_own(candidate: Candidate) -> bool:
    """Whether ``candidate`` may be this clone's own Task: a Task in Backlog
    assigned to this clone's account. A clone claims only a Task its account is
    assigned to (``instance_claims.claim``), so no other Task is its own."""
    return candidate.state == BACKLOG and candidate.assigned


def ordered(ready: Sequence[Candidate], own: Collection[int]) -> list[Candidate]:
    """``ready`` in the order a clone takes it: the Tasks numbered in ``own``,
    this clone's own, first, then the rest. Each part keeps the order of
    :func:`candidates`, by priority, then by number."""
    return [c for c in ready if c.number in own] + [c for c in ready if c.number not in own]


def taken_by_another(resolution: ownership.OwnershipResolution | None, instance: int) -> bool:
    """Whether another instance holds the Task now: its claim is the lowest that
    counts or stands unjudged, as every clone computes the winner (DEC-035
    point 6). An owner that could not be read is no evidence of one."""
    if resolution is None or not resolution.claimants:
        return False
    return min(resolution.claimants) != instance
