"""The rules a lean-business cycle's suspension keeps (DEC-002 point 12): the one predicate
the command that records a suspension and the check share."""

from __future__ import annotations

from datetime import date
from typing import Any

from tests.in_process import load

(suspensions, timeline) = load("lean-business", "suspensions", "timeline")

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
    acts = [suspensions.Act(on(9), "the result of `idea.one`"), suspensions.Act(on(10), "x")]
    [found] = suspensions.breaks(START, 30, [kept], acts)
    assert (found.rule, found.index) == ("over-work", 0)
    assert "2026-12-09" in found.message and "the result of `idea.one`" in found.message


def test_an_ongoing_suspension_covers_every_act_after_its_first_day() -> None:
    ongoing = suspension(0, on(5), on(5))
    acts = [suspensions.Act(on(20, 1, 2027), "the review")]
    assert rules(*suspensions.breaks(START, 30, [ongoing], acts)) == [(0, "over-work")]


def test_its_own_recording_is_no_act_but_another_suspensions_is() -> None:
    one = suspension(0, on(5), on(7), on(10), on(10))
    assert suspensions.breaks(START, 30, [one], []) == []
    other = suspension(1, on(12), on(12), on(14), on(15))
    covering = suspension(0, on(11), on(11), on(16), on(16))
    found = rules(*suspensions.breaks(START, 30, [covering, other], []))
    assert (0, "over-work") in found and (1, "overlap") in found


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


def test_the_cycles_first_planning_is_an_act_of_its_own() -> None:
    cycle = {"planned": {"when": "2026-12-04", "first": {"when": "2026-12-02"}}}
    acts = suspensions.acts_on(cycle, [], None, "c.yaml")
    assert [(act.day, act.what, act.where) for act in acts] == [
        (on(2), "the plan's first planning", "c.yaml#/planned/first"),
        (on(4), "the plan", "c.yaml#/planned"),
    ]


def test_the_acts_are_read_from_the_cycle_its_experiments_and_the_goal() -> None:
    cycle = {"planned": {"when": "2026-11-20"}, "review": {"when": "2027-03-01"}}
    experiment = {
        "id": "idea.one",
        "declared": {"when": "2026-12-02"},
        "stopped": {"when": "2026-12-08"},
        "result": {"when": "2026-12-09"},
        "decision": {"when": "nowhen"},
    }
    acts = suspensions.acts_on(
        cycle, [("e.yaml", experiment)], ("goal.yaml", {"when": "2026-11-01"}), "c.yaml"
    )
    assert [(act.day, act.where) for act in acts] == [
        (on(20, 11), "c.yaml#/planned"),
        (date(2027, 3, 1), "c.yaml#/review"),
        (on(2), "e.yaml#/declared"),
        (on(8), "e.yaml#/stopped"),
        (on(9), "e.yaml#/result"),
        (on(1, 11), "goal.yaml"),
    ]


def test_a_cycles_suspensions_are_held_to_the_rules_from_its_file() -> None:
    cycle = {
        "window": {"start": "2026-12-01", "days": 10},
        "suspensions": [
            {"first-day": "2026-12-20", "when": "2026-12-20"},
        ],
    }
    assert rules(*suspensions.of_cycle(cycle, [])) == [(0, "within-window")]
    assert suspensions.of_cycle({"window": None, "suspensions": cycle["suspensions"]}, []) == []
