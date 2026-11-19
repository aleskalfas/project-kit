"""The rules a cycle's suspension keeps (lean-business DEC-002 point 12).

One predicate holds them, `breaks`: the command that records a suspension refuses one that
breaks them, and the check finds each break an error (point 14). It reads the files alone,
never today's date: an ongoing suspension is one with no day of resuming, whatever today is.

The rules, for each suspension of a cycle:

- **Within the window.** Its first day lies within the cycle's window, as the suspensions
  before it, by their first days, work the window out (`timeline.window`).
- **Not ahead of the clock.** Its first day is no later than the day it was recorded, and its
  day of resuming no later than the day the resumption was recorded.
- **In order.** It resumes no earlier than its first day.
- **Over no work.** No day it covers holds another act recorded on the cycle or its
  experiments, or the idea's goal set (`acts_on`), so a suspension gives back no day on
  which the person recorded work the cycle rests on.
- **One at a time.** The cycle's suspensions do not overlap, so at most one is ongoing.
- **Before the decision.** It, and its resumption, are recorded no later than the cycle's
  decision, since a decided cycle is terminal and takes no act (DEC-003 point 4).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from _lib import timeline
from _lib.reading import day

#: The rules, by the label a break carries.
WITHIN_WINDOW = "within-window"
AHEAD_OF_CLOCK = "ahead-of-clock"
IN_ORDER = "in-order"
OVER_WORK = "over-work"
OVERLAP = "overlap"
AFTER_DECISION = "after-decision"


#: A suspension as a cycle's file records it, read by `timeline.recorded`.
Suspension = timeline.Suspension


@dataclass(frozen=True)
class Act:
    """An act recorded on a day: what it was, in words, such as `the plan`, and where it is
    recorded, a file and a place within it."""

    day: date
    what: str
    where: str = ""


@dataclass(frozen=True)
class Break:
    """A rule a suspension breaks: the suspension's place in the list, the rule's label and
    what breaks it, in words."""

    index: int
    rule: str
    message: str


def acts_on(
    cycle: Mapping[str, object],
    experiments: Iterable[tuple[str, Mapping[str, object]]],
    goal: tuple[str, Mapping[str, object]] | None,
    cycle_file: str = "",
) -> list[Act]:
    """The acts recorded on a cycle and on its experiments, and the idea's goal set, each
    with its day: the cycle's first planning, the last change to its plan and its review,
    each experiment's declaration, stopping rule reached, result and decision, and the goal.
    `experiments` are the cycle's experiments, each with its file; `goal` the idea's goal
    with its file, or None. A suspension's own recording is no act here: `breaks` reads the
    other suspensions itself."""
    acts: list[Act] = []
    planned = cycle.get("planned")
    if isinstance(planned, Mapping):
        _add(
            acts, planned.get("first"), "the plan's first planning", f"{cycle_file}#/planned/first"
        )
    for key, what in (("planned", "the plan"), ("review", "the review")):
        _add(acts, cycle.get(key), what, f"{cycle_file}#/{key}")
    for file, experiment in experiments:
        own = experiment.get("id", file)
        for key, what in (
            ("declared", "the declaration"),
            ("stopped", "the stopping rule reached"),
            ("result", "the result"),
            ("decision", "the decision"),
        ):
            _add(acts, experiment.get(key), f"{what} of `{own}`", f"{file}#/{key}")
    if goal is not None:
        file, data = goal
        _add(acts, data, "the goal set", file)
    return acts


def _add(acts: list[Act], block: object, what: str, where: str) -> None:
    if isinstance(block, Mapping):
        when = day(block.get("when"))
        if when is not None:
            acts.append(Act(when, what, where))


def breaks(
    start: date,
    days: int,
    suspensions: Sequence[Suspension],
    acts: Sequence[Act],
    decided: date | None = None,
) -> list[Break]:
    """Each rule each of `suspensions` breaks, for a cycle whose window is declared from
    `start` for `days` days, under the `acts` recorded on it (`acts_on`), and decided on
    `decided` where it is. In the order of the suspensions, then the rules."""
    found: list[Break] = []
    readable = [s for s in suspensions if s.covered is not None]
    for current in suspensions:
        covered = current.covered
        if covered is None or current.first_day is None:
            continue
        first = current.first_day
        earlier = [
            s.covered
            for s in readable
            if s.covered is not None and s is not current and s.covered.first < first
        ]
        span = timeline.window(start, days, earlier)
        if span.start is None or first < span.start or (span.end is not None and first > span.end):
            found.append(Break(current.index, WITHIN_WINDOW, _outside(first, span)))
        if current.recorded is not None and first > current.recorded:
            found.append(
                Break(
                    current.index,
                    AHEAD_OF_CLOCK,
                    f"its first day, {first}, is later than the day it was recorded, "
                    f"{current.recorded}",
                )
            )
        if current.resumed_at_all:
            found.extend(_resumption(current, first))
        if decided is not None:
            found.extend(_after_decision(current, decided))
        for act in acts:
            if covered.covers(act.day):
                found.append(
                    Break(current.index, OVER_WORK, f"it covers {act.day}, which holds {act.what}")
                )
        for other in suspensions:
            if other is current:
                continue
            for when, what in (
                (other.recorded, "the recording of another suspension"),
                (other.resumption_recorded, "the recording of another suspension's resumption"),
            ):
                if when is not None and covered.covers(when):
                    found.append(
                        Break(current.index, OVER_WORK, f"it covers {when}, which holds {what}")
                    )
        for other in readable:
            if other.index >= current.index or other.covered is None:
                continue
            if _overlap(covered, other.covered):
                found.append(
                    Break(
                        current.index,
                        OVERLAP,
                        f"it overlaps the suspension at place {other.index + 1} of the list",
                    )
                )
    return found


def of_cycle(cycle: Mapping[str, object], acts: Sequence[Act]) -> list[Break]:
    """Each rule each of a cycle's suspensions breaks, from its file as it stands, under the
    `acts` recorded on it (`acts_on`). A command that records a suspension passes the cycle
    with the suspension added, and refuses it where a break names its place. None where the
    cycle's declared window cannot be read."""
    declared = cycle.get("window")
    if not isinstance(declared, Mapping):
        return []
    start, days = day(declared.get("start")), declared.get("days")
    if start is None or isinstance(days, bool) or not isinstance(days, int):
        return []
    review = cycle.get("review")
    decided = day(review.get("when")) if isinstance(review, Mapping) else None
    return breaks(start, days, timeline.recorded(cycle.get("suspensions")), acts, decided)


def _after_decision(current: Suspension, decided: date) -> list[Break]:
    found: list[Break] = []
    for when, what in (
        (current.recorded, "it was recorded"),
        (current.resumption_recorded, "its resumption was recorded"),
    ):
        if when is not None and when > decided:
            found.append(
                Break(
                    current.index,
                    AFTER_DECISION,
                    f"{what} on {when}, after the cycle was decided on {decided}: a decided "
                    f"cycle takes no act",
                )
            )
    return found


def _resumption(current: Suspension, first: date) -> list[Break]:
    found: list[Break] = []
    resumed, noted = current.resumed, current.resumption_recorded
    if resumed is not None and resumed < first:
        found.append(
            Break(
                current.index,
                IN_ORDER,
                f"it resumed on {resumed}, before its first day, {first}",
            )
        )
    if resumed is not None and noted is not None and resumed > noted:
        found.append(
            Break(
                current.index,
                AHEAD_OF_CLOCK,
                f"the day it resumed, {resumed}, is later than the day that was recorded, {noted}",
            )
        )
    return found


def _outside(first: date, span: timeline.Span) -> str:
    if span.start is None:
        return f"its first day, {first}, falls where the window has not started"
    if span.end is None:
        return f"its first day, {first}, falls before the window's first day, {span.start}"
    return (
        f"its first day, {first}, lies outside the window, which runs from {span.start} through "
        f"{span.end} as the suspensions before it work it out"
    )


def _overlap(one: timeline.Covered, other: timeline.Covered) -> bool:
    """Whether two suspensions cover a day in common."""
    if one.resumed is not None and one.resumed <= one.first:
        return False
    if other.resumed is not None and other.resumed <= other.first:
        return False
    starts_before_other_ends = other.resumed is None or one.first < other.resumed
    other_starts_before_one_ends = one.resumed is None or other.first < one.resumed
    return starts_before_other_ends and other_starts_before_one_ends
