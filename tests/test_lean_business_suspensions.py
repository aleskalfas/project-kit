"""The rules a lean-business cycle's suspension keeps (DEC-002 point 12): the one predicate
the command that records a suspension and the check share."""

from __future__ import annotations

from datetime import date
from typing import Any

from tests.in_process import load

(gates, suspensions, timeline) = load("lean-business", "gates", "suspensions", "timeline")

START = date(2026, 12, 1)


def on(day: int, month: int = 12, year: int = 2026) -> date:
    return date(year, month, day)


def suspension(
    index: int,
    first: date | None,
    recorded: date | None,
    resumed: date | None = None,
    noted: date | None = None,
) -> Any:
    return timeline.Suspension(
        index=index,
        first_day=first,
        recorded=recorded,
        resumed=resumed,
        resumption_recorded=noted,
        resumed_at_all=resumed is not None or noted is not None,
    )


def rules(*found: Any) -> list[tuple[int, str]]:
    return [(each.index, each.rule) for each in found]


def test_a_suspension_that_keeps_every_rule_breaks_none() -> None:
    kept = [suspension(0, on(5), on(6), on(10), on(10)), suspension(1, on(20), on(20))]
    acts = [suspensions.Act(on(3), "the declaration"), suspensions.Act(on(12), "the result")]
    assert suspensions.breaks(START, 30, kept, acts) == []


def test_its_first_day_lies_within_the_window() -> None:
    before = suspension(0, on(30, 11), on(30, 11), on(2), on(2))
    after = suspension(0, on(11), on(11))
    assert rules(*suspensions.breaks(START, 10, [before], [])) == [(0, "within-window")]
    assert rules(*suspensions.breaks(START, 10, [after], [])) == [(0, "within-window")]


def test_the_window_is_worked_out_by_the_suspensions_before_it() -> None:
    earlier = suspension(0, on(3), on(3), on(8), on(8))
    later = suspension(1, on(13), on(13))
    assert suspensions.breaks(START, 10, [earlier, later], []) == []
    late = suspension(1, on(16), on(16))
    assert rules(*suspensions.breaks(START, 10, [earlier, late], [])) == [(1, "within-window")]


def test_one_recorded_once_the_window_ran_out_keeps_the_rule_where_its_first_day_lies_in_it() -> (
    None
):
    recorded_late = suspension(0, on(9), on(20), on(21), on(21))
    assert suspensions.breaks(START, 10, [recorded_late], []) == []


def test_its_days_are_no_later_than_the_days_they_were_recorded() -> None:
    ahead = suspension(0, on(6), on(5), on(9), on(8))
    assert rules(*suspensions.breaks(START, 30, [ahead], [])) == [
        (0, "ahead-of-clock"),
        (0, "ahead-of-clock"),
    ]


def test_it_resumes_no_earlier_than_its_first_day() -> None:
    backwards = suspension(0, on(6), on(6), on(4), on(7))
    assert rules(*suspensions.breaks(START, 30, [backwards], [])) == [(0, "in-order")]


def test_no_day_it_covers_holds_another_act() -> None:
    kept = suspension(0, on(5), on(5), on(10), on(10))
    acts = [suspensions.Act(on(9), "the result of `idea--one`"), suspensions.Act(on(10), "x")]
    [found] = suspensions.breaks(START, 30, [kept], acts)
    assert (found.rule, found.index) == ("over-work", 0)
    assert "2026-12-09" in found.message and "the result of `idea--one`" in found.message


def test_an_ongoing_suspension_covers_every_act_after_its_first_day() -> None:
    ongoing = suspension(0, on(5), on(5))
    acts = [suspensions.Act(on(20, 1, 2027), "the review")]
    assert rules(*suspensions.breaks(START, 30, [ongoing], acts)) == [(0, "over-work")]


def test_its_own_recording_is_no_act_but_another_suspensions_is() -> None:
    one = suspension(0, on(5), on(7), on(10), on(10))
    assert suspensions.breaks(START, 30, [one], []) == []
    # Recorded last, the one covered breaks the rules: the one covering stood when it came.
    other = suspension(1, on(12), on(12), on(14), on(15))
    covering = suspension(0, on(11), on(11), on(16), on(16))
    assert rules(*suspensions.breaks(START, 30, [covering, other], [])) == [
        (1, "over-work"),
        (1, "over-work"),
        (1, "overlap"),
    ]
    [recording, _, _] = suspensions.breaks(START, 30, [covering, other], [])
    assert "it was recorded on 2026-12-12, a day the suspension at place 1" in recording.message
    # Recorded last, the one covering breaks them.
    covering_late = suspension(0, on(11), on(17), on(16), on(17))
    assert rules(*suspensions.breaks(START, 30, [covering_late, other], [])) == [
        (0, "over-work"),
        (0, "over-work"),
        (0, "overlap"),
    ]


def test_of_two_recorded_on_one_day_the_later_in_the_list_breaks_the_rules() -> None:
    one = suspension(0, on(11), on(17), on(16), on(17))
    two = suspension(1, on(12), on(17), on(14), on(17))
    assert rules(*suspensions.breaks(START, 30, [one, two], [])) == [(1, "overlap")]


def test_suspensions_do_not_overlap() -> None:
    one = suspension(0, on(5), on(5))
    two = suspension(1, on(20), on(20))
    found = rules(*suspensions.breaks(START, 30, [one, two], []))
    assert (1, "overlap") in found
    apart = [suspension(0, on(5), on(5), on(10), on(10)), suspension(1, on(11), on(11))]
    assert suspensions.breaks(START, 30, apart, []) == []
    # One from the day the other resumed covers the day that resumption was recorded.
    touching = [suspension(0, on(5), on(5), on(10), on(10)), suspension(1, on(10), on(10))]
    assert rules(*suspensions.breaks(START, 30, touching, [])) == [(1, "over-work")]


def test_a_suspension_with_no_readable_first_day_is_left_to_the_schema() -> None:
    assert suspensions.breaks(START, 30, [suspension(0, None, on(5))], []) == []


def test_none_is_recorded_after_the_cycle_was_decided() -> None:
    decided = on(20)
    kept = suspension(0, on(5), on(5), on(10), on(20))
    assert suspensions.breaks(START, 30, [kept], [], decided) == []
    late = suspension(0, on(5), on(21), on(10), on(22))
    [recorded, resumed] = suspensions.breaks(START, 30, [late], [], decided)
    assert (recorded.rule, resumed.rule) == ("after-decision", "after-decision")
    assert "it was recorded on 2026-12-21, after the cycle was decided on 2026-12-20" in (
        recorded.message
    )
    assert "its resumption was recorded on 2026-12-22" in resumed.message


def test_a_cycles_decision_is_read_from_its_review() -> None:
    cycle = {
        "window": {"start": "2026-12-01", "days": 10},
        "suspensions": [{"first-day": "2026-12-03", "when": "2026-12-20"}],
        "review": {"when": "2026-12-19"},
    }
    assert rules(*suspensions.of_cycle(cycle, [])) == [(0, "after-decision")]


# --- contradicting no act already recorded --------------------------------------------------------


def needs_the_window_ended(cycle: dict[str, Any], day: date) -> Any:
    """An act recorded on `day` whose gate refuses it while `cycle`'s window, as the view it
    is asked with gives the cycle, has not ended: as the goal set and the review read it."""

    def ask(view: Any) -> list[Any]:
        span = timeline.cycle_window(view(cycle))
        if span is None or span.end is None or span.end >= day:
            return [gates.Refusal("", "the window has not ended")]
        return []

    return suspensions.Act(day, "the review", "c.yaml", "/review", "review-refused", ask)


def thirty_days(*suspended: dict[str, Any]) -> dict[str, Any]:
    """A cycle whose window runs from 2026-12-01 through 2026-12-30, before `suspended`."""
    return {
        "id": "idea--first",
        "window": {"start": "2026-12-01", "days": 30},
        "suspensions": list(suspended),
    }


def suspended(first: str, resumed: str, recorded: str) -> dict[str, Any]:
    return {
        "first-day": first,
        "when": recorded,
        "resumed": {"day": resumed, "when": recorded},
    }


def test_a_suspension_recorded_late_contradicts_an_act_already_recorded() -> None:
    # Decided on 2026-12-31, after the window ended; recorded on 2027-01-05, the suspension
    # would move its end to 2027-01-01, so the act would read as one its gate refuses.
    late = thirty_days(suspended("2026-12-10", "2026-12-12", "2027-01-05"))
    [found] = suspensions.of_cycle(late, [needs_the_window_ended(late, on(31))])
    assert (found.index, found.rule) == (0, "contradicts")
    assert "counted with it, the review, recorded on 2026-12-31" in found.message
    assert "the window has not ended" in found.message


def test_an_act_recorded_after_the_suspension_is_the_acts_own_to_answer() -> None:
    early = thirty_days(suspended("2026-12-10", "2026-12-12", "2026-12-12"))
    assert suspensions.of_cycle(early, [needs_the_window_ended(early, on(31))]) == []


def test_a_suspension_recorded_on_the_acts_day_contradicts_it() -> None:
    same_day = thirty_days(suspended("2026-12-10", "2026-12-12", "2026-12-31"))
    act = needs_the_window_ended(same_day, on(31))
    assert rules(*suspensions.of_cycle(same_day, [act])) == [(0, "contradicts")]


def test_where_two_contradict_an_act_together_the_one_recorded_last_breaks_the_rule() -> None:
    # Each moves the window's end by one day: alone, to 2026-12-31; together, to 2027-01-01,
    # past the act recorded on 2027-01-01.
    first = suspended("2026-12-10", "2026-12-11", "2027-01-02")
    second = suspended("2026-12-15", "2026-12-16", "2027-01-03")
    for listed, last in (((first, second), 1), ((second, first), 0)):
        cycle = thirty_days(*listed)
        act = needs_the_window_ended(cycle, on(1, 1, 2027))
        assert rules(*suspensions.of_cycle(cycle, [act])) == [(last, "contradicts")]
    # Recorded on one day, the later in the list is the one recorded last.
    same_day = thirty_days(first, {**second, "when": "2027-01-02"})
    act = needs_the_window_ended(same_day, on(1, 1, 2027))
    assert rules(*suspensions.of_cycle(same_day, [act])) == [(1, "contradicts")]


def test_an_act_on_a_day_the_suspension_covers_is_the_rule_over_work() -> None:
    cycle = thirty_days(suspended("2026-12-10", "2026-12-12", "2027-01-05"))
    act = needs_the_window_ended(cycle, on(11))
    assert rules(*suspensions.of_cycle(cycle, [act])) == [(0, "over-work")]


def test_a_cycles_suspensions_are_held_to_the_rules_from_its_file() -> None:
    cycle = {
        "window": {"start": "2026-12-01", "days": 10},
        "suspensions": [
            {"first-day": "2026-12-20", "when": "2026-12-20"},
        ],
    }
    assert rules(*suspensions.of_cycle(cycle, [])) == [(0, "within-window")]
    assert suspensions.of_cycle({"window": None, "suspensions": cycle["suspensions"]}, []) == []
