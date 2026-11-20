"""Where a cycle's window and an experiment's time box fall, once the cycle's suspensions
are counted (lean-business DEC-002 point 12).

The plan's window and each declared time box stay as declared, and where they fall is
worked out here each time it is read, never stored. The process's detections, the commands,
the check and the status all read it here, so none of them disagrees with another on a day.

- **A suspension covers** each day from its first day up to the day the cycle resumed,
  which counts again. One not resumed yet, an *ongoing* suspension, covers every day from
  its first day on, whatever today is.
- **A window** is counted from its declared start. It starts on the first day from then that
  no suspension covers, and ends once it has held as many uncovered days as were declared.
  A window an ongoing suspension reaches has no end yet.
- **A time box** starts on the first day from its declared start that no suspension covers,
  and from then runs its declared days in the calendar, covered or not. So a suspension
  moves it only where it had not started by the suspension's first day, and adds no day to
  it. One whose start an ongoing suspension reaches has no start yet.

Every day is a calendar day, and a window or a time box runs from its first day through its
last (DEC-003 point 1).

**As they stood on a day.** Each reading here counts the suspensions the cycle's data holds.
The detections, the commands and the status read the cycle as it stands, with every
suspension recorded. The check asks a gate of each act with the cycle as its suspensions
stood on the act's day (`stood`): one recorded later counts for nothing, and one whose
resumption was recorded later reads as ongoing. A suspension's rules ask it with and
without one suspension, to tell whether that one contradicts an act (`suspensions`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Any

from _lib.reading import day

_DAY = timedelta(days=1)


@dataclass(frozen=True)
class Covered:
    """The days a suspension covers: from `first` up to `resumed`, which counts again, or
    every day from `first` on where `resumed` is None."""

    first: date
    resumed: date | None = None

    def covers(self, when: date) -> bool:
        return self.first <= when and (self.resumed is None or when < self.resumed)


@dataclass(frozen=True)
class Span:
    """Where a window or a time box falls: its first day and its last, through both. `start`
    is None where an ongoing suspension reached it before it started, and `end` is None
    where it has no end yet."""

    start: date | None
    end: date | None


def span_text(span: Span) -> str:
    """Where a window or a time box falls, in words."""
    if span.start is None:
        return "not started yet"
    if span.end is None:
        return f"from {span.start}, with no end yet"
    return f"{span.start} through {span.end}"


@dataclass(frozen=True)
class Suspension:
    """A suspension as a cycle's file records it: its place in the list, its first day, the
    day it was recorded, and, once the cycle resumed, the day it resumed and the day that was
    recorded. A day that cannot be read is None."""

    index: int
    first_day: date | None
    recorded: date | None
    resumed: date | None = None
    resumption_recorded: date | None = None
    resumed_at_all: bool = False

    @property
    def covered(self) -> Covered | None:
        """The days it covers, or None where its first day cannot be read. One whose day of
        resuming cannot be read is read as ongoing."""
        if self.first_day is None:
            return None
        return Covered(self.first_day, self.resumed if self.resumed_at_all else None)


def recorded(suspensions: object) -> list[Suspension]:
    """A cycle's suspensions as its file writes them, `suspensions`, in the file's order."""
    found: list[Suspension] = []
    for index, entry in enumerate(suspensions if isinstance(suspensions, list) else []):
        if not isinstance(entry, Mapping):
            continue
        resumed = entry.get("resumed")
        resumption = resumed if isinstance(resumed, Mapping) else None
        found.append(
            Suspension(
                index=index,
                first_day=day(entry.get("first-day")),
                recorded=day(entry.get("when")),
                resumed=day(resumption.get("day")) if resumption is not None else None,
                resumption_recorded=day(resumption.get("when")) if resumption is not None else None,
                resumed_at_all=resumption is not None,
            )
        )
    return found


def known_by(suspensions: Sequence[Suspension], as_of: date) -> list[Suspension]:
    """`suspensions` as they stood on `as_of`: each recorded by then, with its resumption
    only where that was recorded by then too, so one resumed later reads as ongoing. A day
    of recording that cannot be read counts as recorded."""
    found: list[Suspension] = []
    for current in suspensions:
        if current.recorded is not None and current.recorded > as_of:
            continue
        noted = current.resumption_recorded
        if current.resumed_at_all and noted is not None and noted > as_of:
            current = replace(current, resumed=None, resumption_recorded=None, resumed_at_all=False)
        found.append(current)
    return found


def stood(
    cycle: Mapping[str, Any], on: date, keep: Callable[[Suspension], bool] | None = None
) -> dict[str, Any]:
    """`cycle`'s data as its suspensions stood on `on` (`known_by`): each recorded by then,
    and that `keep` keeps where it is given, with its resumption only where that was
    recorded by then too. What else the cycle holds is as it stands."""
    written = cycle.get("suspensions")
    entries = written if isinstance(written, list) else []
    kept: list[Any] = []
    for current in known_by(recorded(entries), on):
        if keep is not None and not keep(current):
            continue
        entry = entries[current.index]
        if not current.resumed_at_all and isinstance(entry.get("resumed"), Mapping):
            entry = {key: value for key, value in entry.items() if key != "resumed"}
        kept.append(entry)
    return {**cycle, "suspensions": kept}


def covered_by(suspensions: object) -> list[Covered]:
    """The days each suspension of a cycle covers, from the cycle's `suspensions` as a file
    writes them, in the order of their first days. A suspension with no readable first day
    covers nothing."""
    covered = [s.covered for s in recorded(suspensions)]
    return sorted((c for c in covered if c is not None), key=lambda each: each.first)


def _merged(covered: Iterable[Covered]) -> list[Covered]:
    """The covered days as runs that neither overlap nor touch, in order. A suspension that
    resumes no later than its first day covers nothing."""
    runs: list[Covered] = []
    for current in sorted(covered, key=lambda c: c.first):
        if current.resumed is not None and current.resumed <= current.first:
            continue
        if runs and (runs[-1].resumed is None or current.first <= runs[-1].resumed):
            last = runs[-1]
            if last.resumed is not None and (
                current.resumed is None or current.resumed > last.resumed
            ):
                runs[-1] = Covered(last.first, current.resumed)
            continue
        runs.append(current)
    return runs


def first_uncovered(start: date, covered: Sequence[Covered]) -> date | None:
    """The first day from `start` that no suspension covers, or None where an ongoing one
    covers every day from `start` on."""
    when = start
    for run in _merged(covered):
        if run.covers(when):
            if run.resumed is None:
                return None
            when = run.resumed
    return when


def window(start: date, days: int, covered: Sequence[Covered]) -> Span:
    """Where a window declared from `start` for `days` days falls under the suspensions
    that cover `covered`."""
    first = first_uncovered(start, covered)
    if first is None:
        return Span(None, None)
    remaining = days
    when = first
    for run in _merged(covered):
        if run.resumed is not None and run.resumed <= when:
            continue
        if run.first > when:
            free = (run.first - when).days
            if free >= remaining:
                return Span(first, when + (remaining - 1) * _DAY)
            remaining -= free
        if run.resumed is None:
            return Span(first, None)
        when = run.resumed
    return Span(first, when + (remaining - 1) * _DAY)


def time_box(start: date, end: date, covered: Sequence[Covered]) -> Span:
    """Where a time box declared from `start` through `end` falls under the suspensions that
    cover `covered`: moved later only where they covered its start, its declared days
    kept."""
    first = first_uncovered(start, covered)
    if first is None:
        return Span(None, None)
    return Span(first, first + (end - start))


# --- read from the files --------------------------------------------------------------------------


def cycle_window(cycle: Mapping[str, object]) -> Span | None:
    """Where a cycle's window falls, under the suspensions its data holds. None where its
    declared window cannot be read."""
    declared = cycle.get("window")
    if not isinstance(declared, Mapping):
        return None
    start, days = day(declared.get("start")), declared.get("days")
    if start is None or isinstance(days, bool) or not isinstance(days, int):
        return None
    return window(start, days, covered_by(cycle.get("suspensions")))


def experiment_time_box(
    experiment: Mapping[str, object], cycle: Mapping[str, object] | None
) -> Span | None:
    """Where an experiment's time box falls, under the suspensions its cycle's data holds.
    None where its declared days cannot be read. Without its cycle, no suspension moves
    it."""
    start, end = day(experiment.get("start")), day(experiment.get("end"))
    if start is None or end is None:
        return None
    suspensions = cycle.get("suspensions") if cycle is not None else None
    return time_box(start, end, covered_by(suspensions))


def ran_through(box: Span, cycle: Mapping[str, object]) -> bool:
    """Whether a suspension `cycle`'s data holds covers a day of the time box `box`: a time
    box the suspension ran through, which one it moved past does not."""
    if box.start is None:
        return False
    for covered in covered_by(cycle.get("suspensions")):
        reaches = box.end is None or covered.first <= box.end
        if covered.resumed is not None and covered.resumed <= covered.first:
            continue
        if reaches and (covered.resumed is None or box.start < covered.resumed):
            return True
    return False
