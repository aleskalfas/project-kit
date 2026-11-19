"""Where lean-business's windows and time boxes fall under a cycle's suspensions (DEC-002
point 12): the one predicate the check, the commands, the status and the process's
detections share."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.in_process import load

(timeline,) = load("lean-business", "timeline")

Covered = timeline.Covered
Span = timeline.Span

START = date(2026, 12, 1)


def on(day: int, month: int = 12, year: int = 2026) -> date:
    return date(year, month, day)


# --- a window -----------------------------------------------------------------------------------


def test_a_window_with_no_suspension_runs_its_days_from_its_start() -> None:
    assert timeline.window(START, 90, []) == Span(START, START + timedelta(days=89))
    assert timeline.window(START, 1, []) == Span(START, START)


def test_a_suspension_that_covers_its_start_moves_where_it_starts() -> None:
    covered = [Covered(on(1, 11), on(5))]
    assert timeline.window(START, 10, covered) == Span(on(5), on(14))


def test_a_suspension_inside_it_adds_the_days_it_covers_to_its_end() -> None:
    covered = [Covered(on(5), on(8))]
    assert timeline.window(START, 10, covered) == Span(START, on(13))


def test_a_suspension_before_its_start_or_after_its_end_moves_nothing() -> None:
    covered = [Covered(on(1, 11), on(20, 11)), Covered(on(20), on(25))]
    assert timeline.window(START, 10, covered) == Span(START, on(10))


def test_a_suspension_that_resumes_on_its_first_day_covers_nothing() -> None:
    assert timeline.window(START, 10, [Covered(on(5), on(5))]) == Span(START, on(10))


def test_an_ongoing_suspension_the_window_reaches_leaves_it_no_end() -> None:
    assert timeline.window(START, 10, [Covered(on(5))]) == Span(START, None)
    assert timeline.window(START, 10, [Covered(on(30, 11))]) == Span(None, None)


def test_an_ongoing_suspension_after_its_end_leaves_its_end() -> None:
    assert timeline.window(START, 10, [Covered(on(11))]) == Span(START, on(10))


def test_suspensions_that_overlap_count_each_day_once() -> None:
    covered = [Covered(on(5), on(10)), Covered(on(8), on(12)), Covered(on(12), on(13))]
    assert timeline.window(START, 10, covered) == Span(START, on(18))


def test_many_suspensions_move_it_by_every_day_they_cover() -> None:
    covered = [Covered(on(3), on(4)), Covered(on(6), on(9)), Covered(on(20), on(22))]
    assert timeline.window(START, 10, covered) == Span(START, on(14))


@pytest.mark.parametrize("days", [1, 2, 3, 30])
def test_the_window_holds_its_days_uncovered(days: int) -> None:
    covered = [Covered(on(3), on(6)), Covered(on(10))]
    span = timeline.window(START, days, covered)
    if span.end is None:
        held = [START + timedelta(n) for n in range((on(10) - START).days)]
        assert len([d for d in held if not any(c.covers(d) for c in covered)]) < days
        return
    assert span.start is not None
    run = [span.start + timedelta(n) for n in range((span.end - span.start).days + 1)]
    assert len([d for d in run if not any(c.covers(d) for c in covered)]) == days


# --- a time box ---------------------------------------------------------------------------------


def test_a_time_box_started_before_a_suspension_keeps_its_dates() -> None:
    assert timeline.time_box(on(1), on(14), [Covered(on(5), on(20))]) == Span(on(1), on(14))


def test_a_suspension_that_covers_its_start_moves_it_whole_and_adds_no_day() -> None:
    assert timeline.time_box(on(5), on(18), [Covered(on(3), on(10))]) == Span(on(10), on(23))


def test_a_suspension_that_ended_before_its_start_moves_it_not_at_all() -> None:
    assert timeline.time_box(on(5), on(18), [Covered(on(1), on(4))]) == Span(on(5), on(18))


def test_an_earlier_move_brings_it_under_a_later_suspension() -> None:
    covered = [Covered(on(3), on(10)), Covered(on(10), on(12))]
    assert timeline.time_box(on(5), on(6), covered) == Span(on(12), on(13))


def test_an_ongoing_suspension_that_reaches_its_start_leaves_it_no_start() -> None:
    assert timeline.time_box(on(5), on(18), [Covered(on(5))]) == Span(None, None)
    assert timeline.time_box(on(5), on(18), [Covered(on(6))]) == Span(on(5), on(18))


# --- read from the files ------------------------------------------------------------------------


def test_a_cycles_window_is_read_from_its_file() -> None:
    cycle = {
        "window": {"start": "2026-12-01", "days": 10},
        "suspensions": [
            {"first-day": "2026-12-05", "when": "2026-12-05", "resumed": {"day": "2026-12-08"}},
        ],
    }
    assert timeline.cycle_window(cycle) == Span(START, on(13))


def test_a_suspension_whose_day_of_resuming_cannot_be_read_is_read_as_ongoing() -> None:
    cycle = {
        "window": {"start": "2026-12-01", "days": 10},
        "suspensions": [{"first-day": "2026-12-05", "resumed": {"day": "soon"}}],
    }
    assert timeline.cycle_window(cycle) == Span(START, None)


@pytest.mark.parametrize(
    "window",
    [
        None,
        {"start": "2026-12-01"},
        {"start": "someday", "days": 3},
        {"start": "2026-12-01", "days": True},
    ],
)
def test_a_window_that_cannot_be_read_falls_nowhere(window: object) -> None:
    assert timeline.cycle_window({"window": window}) is None


def test_an_experiments_time_box_is_read_from_its_file_and_its_cycles() -> None:
    experiment = {"start": "2026-12-05", "end": "2026-12-18"}
    cycle = {"suspensions": [{"first-day": "2026-12-03", "resumed": {"day": "2026-12-10"}}]}
    assert timeline.experiment_time_box(experiment, cycle) == Span(on(10), on(23))
    assert timeline.experiment_time_box(experiment, None) == Span(on(5), on(18))
    assert timeline.experiment_time_box({"start": "2026-12-05"}, cycle) is None


def test_the_suspensions_are_read_in_the_files_order_with_each_day_recorded() -> None:
    recorded = timeline.recorded(
        [
            {"first-day": "2026-12-10", "when": "2026-12-11"},
            "not a suspension",
            {
                "first-day": "2026-12-01",
                "when": "2026-12-01",
                "resumed": {"day": "2026-12-04", "when": "2026-12-05"},
            },
        ]
    )
    assert [(s.index, s.first_day, s.recorded) for s in recorded] == [
        (0, on(10), on(11)),
        (2, on(1), on(1)),
    ]
    assert recorded[1].covered == Covered(on(1), on(4))
    assert recorded[0].covered == Covered(on(10))
    assert timeline.covered_by([{"first-day": "x"}, {"first-day": "2026-12-01"}]) == [
        Covered(on(1))
    ]
