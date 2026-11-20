"""The rules a cycle's suspension keeps (lean-business DEC-002 point 12).

One predicate holds them, `of_cycle`: the command that records a suspension refuses one that
breaks them, and the check finds each break an error (point 14). It reads the files alone,
never today's date: an ongoing suspension is one with no day of resuming, whatever today is.

The rules, for each suspension of a cycle:

- **Within the window.** Its first day lies within the cycle's window, as the suspensions
  before it, by their first days, work the window out (`timeline.window`).
- **Not ahead of the clock.** Its first day is no later than the day it was recorded, and its
  day of resuming no later than the day the resumption was recorded.
- **In order.** It resumes no earlier than its first day.
- **Over no work.** No day it covers holds another act recorded on the cycle or its
  experiments, or the idea's goal set (`acts.bearing_on`), so a suspension gives back no day
  on which the person recorded work the cycle rests on.
- **One at a time.** The cycle's suspensions do not overlap, so at most one is ongoing.
- **Contradicting no act.** Counted with it, no act recorded on or before the day it was
  recorded reads as one its gate refuses, where the gate let it through without it
  (`contradictions`): a suspension recorded late may move a window's end, or a time box
  not yet started, past an act that needed it ended.
- **Before the decision.** It, and its resumption, are recorded no later than the cycle's
  decision, since a decided cycle is terminal and takes no act (DEC-003 point 4).

**Recorded last.** Where two suspensions together break a rule, or a suspension and an act
of the same day, the break is the suspension's recorded last: of two recorded on one day,
the later in the list, which a command appends. So the command that records a suspension
refuses the one it records, and the check finds the break at the same one.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from _lib import timeline
from _lib.acts import Act, View
from _lib.reading import day

#: The rules, by the label a break carries.
WITHIN_WINDOW = "within-window"
AHEAD_OF_CLOCK = "ahead-of-clock"
IN_ORDER = "in-order"
OVER_WORK = "over-work"
OVERLAP = "overlap"
CONTRADICTS = "contradicts"
AFTER_DECISION = "after-decision"


#: A suspension as a cycle's file records it, read by `timeline.recorded`.
Suspension = timeline.Suspension


@dataclass(frozen=True)
class Break:
    """A rule a suspension breaks: the suspension's place in the list, the rule's label and
    what breaks it, in words."""

    index: int
    rule: str
    message: str


def recorded_order(suspension: Suspension) -> tuple[date, int]:
    """Where a suspension falls in the order the suspensions were recorded: by the day it
    was recorded, then by its place in the list. A day that cannot be read counts as the
    earliest, as `timeline.known_by` counts it recorded."""
    return (suspension.recorded or date.min, suspension.index)


def breaks(
    start: date,
    days: int,
    suspensions: Sequence[Suspension],
    acts: Sequence[Act],
    decided: date | None = None,
) -> list[Break]:
    """Each rule each of `suspensions` breaks, for a cycle whose window is declared from
    `start` for `days` days, under the `acts` recorded on it (`acts.bearing_on`), and decided
    on `decided` where it is, but contradicting no act, which needs the cycle's data
    (`contradictions`). In the order of the suspensions, then the rules."""
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
            if other is not current:
                found.extend(_over_recording(current, covered, other))
        for other in readable:
            if other.covered is None or recorded_order(other) >= recorded_order(current):
                continue
            if _overlap(covered, other.covered):
                found.append(
                    Break(
                        current.index,
                        OVERLAP,
                        f"it overlaps the suspension at place {other.index + 1} of the list",
                    )
                )
    return sorted(found, key=lambda each: each.index)


def _over_recording(
    covering: Suspension, covered: timeline.Covered, other: Suspension
) -> list[Break]:
    """Where `covering`, which covers `covered`, covers a day on which `other` or its
    resumption was recorded: a break of the one of the two recorded last."""
    found: list[Break] = []
    later = recorded_order(covering) > recorded_order(other)
    for when, what, noted in (
        (other.recorded, "the recording of another suspension", "it was recorded"),
        (
            other.resumption_recorded,
            "the recording of another suspension's resumption",
            "its resumption was recorded",
        ),
    ):
        if when is None or not covered.covers(when):
            continue
        if later:
            found.append(Break(covering.index, OVER_WORK, f"it covers {when}, which holds {what}"))
        else:
            found.append(
                Break(
                    other.index,
                    OVER_WORK,
                    f"{noted} on {when}, a day the suspension at place {covering.index + 1} of "
                    f"the list covers",
                )
            )
    return found


def contradictions(cycle: Mapping[str, Any], acts: Sequence[Act]) -> list[Break]:
    """Each act a suspension of `cycle` contradicts: counted with it, an act recorded no
    later than the day the suspension was recorded reads as one its gate refuses, though
    the gate lets it through without it. Each suspension is counted with those recorded
    before it (`recorded_order`), as they stood on the day it was recorded, and each other
    cycle as its suspensions stood that day, but for those recorded on it. So where several
    together contradict an act, the break is the one's recorded last. An act on a day the
    suspension covers is the rule over work's, and a suspension whose day of recording
    cannot be read is the shape's."""
    found: list[Break] = []
    for current in timeline.recorded(cycle.get("suspensions")):
        on, covered = current.recorded, current.covered
        if on is None:
            continue
        with_it = _view(cycle, on, _recorded_by(current, counted=True))
        without = _view(cycle, on, _recorded_by(current, counted=False))
        for act in acts:
            if act.ask is None or act.day > on:
                continue
            if covered is not None and covered.covers(act.day):
                continue
            refused = act.ask(with_it)
            if refused and not act.ask(without):
                found.append(
                    Break(
                        current.index,
                        CONTRADICTS,
                        f"counted with it, {act.what}, recorded on {act.day}, reads as one its "
                        f"gate refuses: {refused[0].message}",
                    )
                )
    return found


def _recorded_by(current: Suspension, *, counted: bool) -> Callable[[Suspension], bool]:
    """Keeps each suspension recorded before `current`, and `current` itself where it is
    `counted`."""
    mine = recorded_order(current)
    if counted:
        return lambda suspension: recorded_order(suspension) <= mine
    return lambda suspension: recorded_order(suspension) < mine


def _view(cycle: Mapping[str, Any], on: date, keep: Callable[[Suspension], bool]) -> View:
    """How each cycle is read where `cycle`'s suspensions that `keep` keeps are counted, as
    they stood on `on`: `cycle` itself so, and another as its suspensions stood on `on`,
    but for those recorded on it, which may have come after. `cycle` is told by its id, so a
    command may give it with a suspension not yet written."""
    own = cycle.get("id")

    def view(other: Mapping[str, Any]) -> Mapping[str, Any]:
        if other is cycle or (own is not None and other.get("id") == own):
            return timeline.stood(cycle, on, keep)
        return timeline.stood(other, on, lambda s: s.recorded != on)

    return view


def of_cycle(cycle: Mapping[str, Any], acts: Sequence[Act]) -> list[Break]:
    """Each rule each of a cycle's suspensions breaks, from its file as it stands, under the
    `acts` its suspensions bear on (`acts.bearing_on`). A command that records a suspension
    passes the cycle with the suspension added, and refuses it where a break names its
    place. None where the cycle's declared window cannot be read."""
    declared = cycle.get("window")
    if not isinstance(declared, Mapping):
        return []
    start, days = day(declared.get("start")), declared.get("days")
    if start is None or isinstance(days, bool) or not isinstance(days, int):
        return []
    review = cycle.get("review")
    decided = day(review.get("when")) if isinstance(review, Mapping) else None
    listed = timeline.recorded(cycle.get("suspensions"))
    return [*breaks(start, days, listed, acts, decided), *contradictions(cycle, acts)]


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
