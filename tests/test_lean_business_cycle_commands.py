"""lean-business's suspensions, reviews and briefing (lean-business DEC-001 point 10; DEC-002
points 11, 12 and 15; DEC-003 points 4 and 5): a cycle suspended, resumed and reviewed, and
the status that orients a person coming back to an idea.

Each runs in this process on a copy of the fixture idea, on a day the test names, against
an engine that asks the same predicates as the engine itself (`tests/lean_business_world.py`).
The fixture's cycle, `first`, has a window from 2026-11-01 for 90 days, was suspended from
2026-12-20 until 2027-01-03, and was reviewed on 2027-02-15; its two experiments are
decided. A second cycle, planned here after it, has a window from 2027-03-10 for 60 days,
through 2027-05-08, and its draft a time box from 2027-03-12 through 2027-03-25."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from tests import lean_business_world as lb

#: A day after the fixture's cycle was decided, when the next may be planned.
DAY = date(2027, 3, 1)

FIRST = "meal-plan--first"
SECOND = "meal-plan--second"
SECOND_FILE = f"{lb.IDEA}/cycles/second.yaml"
PLAN = (
    "--variant",
    "direct",
    "--start",
    "2027-03-10",
    "--days",
    "60",
    "--objective",
    "Show that households keep paying for a planned week",
    "--key-result",
    "direct:revenue:30",
    "--constraint-step",
    "revenue",
    "--constraint-evidence",
    "Few of those who came back paid",
)

DRAFT = "meal-plan--weekly-calls"
DRAFT_FILE = f"{lb.IDEA}/experiments/weekly-calls.yaml"
LANDING_PAGE = "meal-plan--landing-page"

#: The prompts of the cycle's process definition.
RESUME_PROMPT = (
    "Resume the cycle on the day given, the day you came back? Its days count again from then, "
    "and its window falls later by the days the suspension covered; where the window, so moved, "
    "has ended, the cycle goes into review."
)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> lb.World:
    return lb.world(tmp_path, monkeypatch, DAY)


def on(world: lb.World, day: date) -> None:
    world.engine.on = day


def planned(world: lb.World) -> None:
    """The second cycle planned on `DAY`."""
    run = world.run("plan_cycle", SECOND, *PLAN, "--person-decided")
    assert run.code == 0, run.err


def declared(world: lb.World) -> None:
    """The second cycle planned, and a generative experiment in it declared on `DAY`."""
    planned(world)
    run = world.run(
        "new_experiment",
        DRAFT,
        "--kind",
        "generative",
        "--assumption",
        "direct--planning-takes-long",
        "--cycle",
        "second",
    )
    assert run.code == 0, run.err
    run = world.run(
        "draft_experiment",
        DRAFT,
        "--learn",
        "Whether a weekly call keeps households planning",
        "--stopping-rule",
        "Twelve calls, or three in a row that bring nothing new",
        "--fit",
        "8/calls that tell the same story",
        "--start",
        "2027-03-12",
        "--end",
        "2027-03-25",
    )
    assert run.code == 0, run.err
    assert world.run("record_estimate", DRAFT, "6", "--person-decided").code == 0
    assert world.run("declare", DRAFT, "--person-decided").code == 0


def first_only(world: lb.World, change: Any = None) -> None:
    """The fixture's first cycle with its review taken away, and with `change` made to it,
    and with no experiment beside it."""
    for experiment in (world.root / lb.IDEA / "experiments").iterdir():
        experiment.unlink()

    def edited(data: Any) -> None:
        del data["review"]
        if change is not None:
            change(data)

    world.edit(lb.CYCLE, edited)


def suspended_on_day_50(data: Any) -> None:
    """Decision 23's example: the window's day 50, 2026-12-20, the first day away, and the
    suspension recorded on day 120, 2027-02-28, not yet resumed."""
    data["suspensions"] = [
        {
            "reason": "A family matter",
            "first-day": date(2026, 12, 20),
            "by": lb.PERSON,
            "when": date(2027, 2, 28),
        }
    ]


def cycle_moves(world: lb.World) -> list[tuple[str, str, str, str, str]]:
    return [move for move in world.engine.moves if move[0] == "cycle-lifecycle"]


def briefing(world: lb.World) -> dict[str, Any]:
    run = world.run("status", "meal-plan", "--json")
    assert run.code == 0, run.err
    (idea,) = json.loads(run.out)["ideas"]
    return idea


# --- suspend ----------------------------------------------------------------------------------


def test_suspend_records_an_ongoing_suspension_and_moves_the_cycle_into_suspended(
    world: lb.World,
) -> None:
    declared(world)
    on(world, date(2027, 3, 20))
    run = world.run(
        "suspend",
        SECOND,
        "--reason",
        "A move of house",
        "--since",
        "2027-03-18",
        "--person-decided",
    )
    assert run.code == 0, run.err
    assert world.read(SECOND_FILE)["suspensions"] == [
        {
            "reason": "A move of house",
            "first-day": date(2027, 3, 18),
            "by": lb.PERSON,
            "when": date(2027, 3, 20),
        }
    ]
    assert cycle_moves(world) == [("cycle-lifecycle", SECOND, "running", "suspended", lb.PERSON)]
    assert (
        "Its window: 2027-03-10 through 2027-05-08 before this, from 2027-03-10, with no end "
        "yet after it." in run.out
    )
    assert (
        f"`{DRAFT}` had started by 2027-03-18, so it keeps its time box, 2027-03-12 through "
        f"2027-03-25" in run.out
    )
    assert f"`pkit lean resume {SECOND}` resumes it" in run.out


def test_suspend_moves_an_experiment_not_started_by_its_first_day(world: lb.World) -> None:
    declared(world)
    on(world, date(2027, 3, 14))
    run = world.run(
        "suspend",
        SECOND,
        "--reason",
        "Ill",
        "--since",
        "2027-03-11",
        "--resumed",
        "2027-03-13",
        "--person-decided",
    )
    assert run.code == 0, run.err
    assert world.read(SECOND_FILE)["suspensions"][0]["resumed"] == {
        "day": date(2027, 3, 13),
        "by": lb.PERSON,
        "when": date(2027, 3, 14),
    }
    assert (
        f"`{DRAFT}`'s time box: 2027-03-12 through 2027-03-25 before this, 2027-03-13 through "
        f"2027-03-26 after it." in run.out
    )
    assert "2027-03-10 through 2027-05-10 after it" in run.out
    # Running before the write and after it, the cycle takes no move.
    assert cycle_moves(world) == []


def test_suspend_recorded_late_takes_a_cycle_in_review_back_to_running(world: lb.World) -> None:
    planned(world)
    on(world, date(2027, 5, 12))
    run = world.run(
        "suspend",
        SECOND,
        "--reason",
        "Family",
        "--since",
        "2027-04-01",
        "--resumed",
        "2027-04-11",
        "--person-decided",
    )
    assert run.code == 0, run.err
    assert cycle_moves(world) == [("cycle-lifecycle", SECOND, "in-review", "running", lb.PERSON)]
    assert "2027-03-10 through 2027-05-18 after it" in run.out


def test_suspend_refuses_a_cycle_planned_suspended_or_decided(world: lb.World) -> None:
    planned(world)
    run = world.run("suspend", SECOND, "--reason", "Ill", "--since", "2027-03-01")
    assert run.code == 1
    assert "is planned, and its window has not started, on 2027-03-10" in run.err
    assert f"`pkit lean change-plan {SECOND} --days <n>`" in run.err
    run = world.run("suspend", FIRST, "--reason", "Ill", "--since", "2027-03-01")
    assert run.code == 1
    assert f"`{FIRST}` is decided" in run.err
    on(world, date(2027, 3, 20))
    argv = ("--reason", "Ill", "--since", "2027-03-18", "--person-decided")
    assert world.run("suspend", SECOND, *argv).code == 0
    run = world.run("suspend", SECOND, *argv)
    assert run.code == 1
    assert (
        f"is suspended already: nothing is recorded on a suspended cycle but resuming it, "
        f"`pkit lean resume {SECOND}`" in run.err
    )


@pytest.mark.parametrize(
    "argv",
    [
        ("suspend", "first", "--reason", "Ill", "--since", "2027-03-01"),
        ("resume", "first"),
        ("review_cycle", "first", "--reached", "1", "--decision", "persevere", "--reasons", "-"),
    ],
)
def test_the_cycle_commands_read_a_cycle_by_its_own_part(
    world: lb.World, argv: tuple[str, ...]
) -> None:
    run = world.run(*argv)
    assert run.code == 1
    assert "no cycle's id" not in run.err
    assert f"`{FIRST}`" in run.err


def test_suspend_refuses_a_suspension_that_breaks_its_rules(world: lb.World) -> None:
    declared(world)
    on(world, date(2027, 3, 15))
    assert world.run("reach_stopping_rule", DRAFT, "--person-decided").code == 0
    on(world, date(2027, 3, 20))
    kept = lb.snapshot(world.root)
    # A covered day that holds recorded work: the stopping rule reached on 2027-03-15.
    run = world.run(
        "suspend", SECOND, "--reason", "Ill", "--since", "2027-03-14", "--person-decided"
    )
    assert run.code == 1
    assert "the suspension breaks its rules" in run.err
    assert "2027-03-15" in run.err
    # A first day later than today.
    run = world.run(
        "suspend", SECOND, "--reason", "Ill", "--since", "2027-03-25", "--person-decided"
    )
    assert run.code == 1
    assert "the suspension breaks its rules" in run.err
    run = world.run("suspend", SECOND, "--reason", " ", "--since", "2027-03-18")
    assert run.code == 1
    assert "give --reason its words" in run.err
    assert lb.snapshot(world.root) == kept


def test_suspend_off_a_terminal_prints_its_question_and_writes_nothing(world: lb.World) -> None:
    planned(world)
    on(world, date(2027, 3, 20))
    kept = lb.snapshot(world.root)
    run = world.run("suspend", SECOND, "--reason", "Ill", "--since", "2027-03-18")
    assert run.code == 3
    assert (
        f"Record that your life stopped `{SECOND}` from 2027-03-18, for this reason: Ill?"
        in run.out + run.err
    )
    assert lb.snapshot(world.root) == kept


# --- resume -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("resumed", "lands"),
    [
        (date(2027, 1, 19), "running"),
        (date(2027, 1, 18), "in-review"),
        (date(2026, 12, 30), "in-review"),
    ],
    ids=["on-day-80-into-running", "on-day-79-into-review", "on-day-60-into-review"],
)
def test_resume_lands_in_running_or_in_review_as_decision_23s_example_has_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, resumed: date, lands: str
) -> None:
    # Decision 23's example: a window of days 1 to 90, suspended on day 50 and recorded on
    # day 120. Resumed on day 80 or later, its window, moved, holds today; earlier, it ended
    # before today, and the cycle goes into review.
    world = lb.world(tmp_path, monkeypatch, date(2027, 2, 28))
    first_only(world, suspended_on_day_50)
    run = world.run("resume", FIRST, "--on", resumed.isoformat(), "--person-decided")
    assert run.code == 0, run.err
    assert cycle_moves(world) == [("cycle-lifecycle", FIRST, "suspended", lands, lb.PERSON)]
    assert world.read(lb.CYCLE)["suspensions"][0]["resumed"] == {
        "day": resumed,
        "by": lb.PERSON,
        "when": date(2027, 2, 28),
    }
    assert f"`{FIRST}` moved from suspended to {lands}." in run.out


def test_resume_takes_today_where_no_day_is_given_and_asks_the_definitions_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = lb.world(tmp_path, monkeypatch, date(2027, 2, 28))
    first_only(world, suspended_on_day_50)
    run = world.run("resume", FIRST, terminal=True, answers=[True])
    assert run.code == 0, run.err
    assert run.asked == [RESUME_PROMPT]
    assert world.read(lb.CYCLE)["suspensions"][0]["resumed"]["day"] == date(2027, 2, 28)
    assert (
        f"Resuming `{FIRST}` on 2027-02-28: the suspension from 2026-12-20 until 2027-02-28, "
        f"70 days: A family matter; recorded on 2027-02-28, 70 days after its first day." in run.out
    )
    assert (
        "Its window: from 2026-11-01, with no end yet before this, 2026-11-01 through "
        "2027-04-09 after it." in run.out
    )
    assert cycle_moves(world) == [("cycle-lifecycle", FIRST, "suspended", "running", lb.PERSON)]


def test_resume_refuses_a_cycle_not_suspended_and_a_day_its_rules_refuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = lb.world(tmp_path, monkeypatch, date(2027, 2, 28))
    first_only(world, suspended_on_day_50)
    kept = lb.snapshot(world.root)
    run = world.run("resume", FIRST, "--on", "2026-12-10", "--person-decided")
    assert run.code == 1
    assert "resuming on 2026-12-10 breaks the suspension's rules" in run.err
    run = world.run("resume", FIRST, "--on", "2027-03-01", "--person-decided")
    assert run.code == 1
    assert lb.snapshot(world.root) == kept
    assert world.run("resume", FIRST, "--person-decided").code == 0
    run = world.run("resume", FIRST, "--person-decided")
    assert run.code == 1
    assert f"`{FIRST}` stands running, not suspended: only a suspended cycle resumes" in run.err


def test_resume_refuses_a_suspended_cycle_with_no_suspension_or_two_to_resume_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The engine reads a cycle suspended only where one suspension is ongoing, so the first
    # case needs an engine that disagrees with the file: here, the fixture's suspension,
    # resumed, is all the file holds. Two ongoing at once are a break the engine lets through.
    world = lb.world(tmp_path, monkeypatch, date(2027, 2, 28))
    first_only(world)
    kept = lb.snapshot(world.root)
    with monkeypatch.context() as stubbed:
        stubbed.setattr(world.engine, "_state", lambda process, subject: "suspended")
        run = world.run("resume", FIRST, "--person-decided")
    assert run.code == 1
    assert (
        f"`{FIRST}` stands suspended, yet records no suspension without a resumption, so there "
        f"is none to resume from" in run.err
    )
    assert "leaves it suspended" not in run.err
    assert lb.snapshot(world.root) == kept

    def twice(data: Any) -> None:
        suspended_on_day_50(data)
        data["suspensions"].append(dict(data["suspensions"][0], **{"first-day": date(2027, 1, 5)}))

    world.edit(lb.CYCLE, twice)
    run = world.run("resume", FIRST, "--person-decided")
    assert run.code == 1
    assert f"`{FIRST}` has 2 suspensions ongoing, and resuming from one leaves it" in run.err


# --- review-cycle -----------------------------------------------------------------------------


def in_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> lb.World:
    """The fixture's cycle on 2027-02-15, after its window, its review taken away."""
    world = lb.world(tmp_path, monkeypatch, date(2027, 2, 15))
    world.edit(lb.CYCLE, lambda data: data.pop("review"))
    return world


def test_review_cycle_records_the_review_after_its_progress_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = in_review(tmp_path, monkeypatch)
    run = world.run(
        "review_cycle",
        FIRST,
        "--reached",
        "52",
        "--decision",
        "persevere",
        "--reasons",
        "Retention passed its target",
        "--person-decided",
    )
    assert run.code == 0, run.err
    assert world.read(lb.CYCLE)["review"] == {
        "reached": [52],
        "winning": "[canvas:meal-plan--direct]",
        "decision": "persevere",
        "reasons": "Retention passed its target",
        "by": lb.PERSON,
        "when": date(2027, 2, 15),
    }
    assert cycle_moves(world) == [("cycle-lifecycle", FIRST, "in-review", "decided", lb.PERSON)]
    report = run.out.splitlines()
    assert report[:3] == [
        f"The progress report of `{FIRST}`:",
        "  `meal-plan--direct`, retention: reached 52 of 40, met",
        "  Suspended from 2026-12-20 until 2027-01-03, 14 days: A family matter over the turn "
        "of the year; recorded on 2026-12-21, 1 day after its first day",
    ]
    assert "[persevere-missed]" not in run.out


def test_review_cycle_warns_when_persevering_on_a_missed_objective(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = in_review(tmp_path, monkeypatch)
    run = world.run(
        "review_cycle",
        FIRST,
        "--reached",
        "30",
        "--winning",
        "direct",
        "--decision",
        "persevere",
        "--reasons",
        "A near miss with a clear cause",
        "--person-decided",
    )
    assert run.code == 0, run.err
    assert "  `meal-plan--direct`, retention: reached 30 of 40, missed" in run.out
    assert "`meal-plan--direct` missed the objective, so persevering draws a warning" in run.out
    assert "[persevere-missed]" in run.out


def test_review_cycle_pivots_only_on_a_decided_experiment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = in_review(tmp_path, monkeypatch)
    pivot = ("--reached", "30", "--decision", "pivot", "--reasons", "Pay per week instead")
    run = world.run("review_cycle", FIRST, *pivot, "--person-decided")
    assert run.code == 1
    assert "a pivot names at least one as its evidence" in run.err
    run = world.run("review_cycle", FIRST, *pivot, "--evidence", "landing-page", "--person-decided")
    assert run.code == 0, run.err
    assert world.read(lb.CYCLE)["review"]["evidence"] == [f"[experiment:{LANDING_PAGE}]"]


def test_review_cycle_refuses_what_its_review_cannot_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = in_review(tmp_path, monkeypatch)
    kept = lb.snapshot(world.root)
    decision = ("--decision", "persevere", "--reasons", "It worked")
    run = world.run("review_cycle", FIRST, "--reached", "52", "--reached", "3", *decision)
    assert run.code == 1
    assert "--reached gives 2 numbers, and the objective has 1 key result" in run.err
    run = world.run("review_cycle", FIRST, "--reached", "many", *decision)
    assert run.code == 1
    assert "--reached is a number, and `many` is none" in run.err
    run = world.run("review_cycle", FIRST, "--reached", "52", "--winning", "two-sided", *decision)
    assert run.code == 1
    assert "the winning variant, `meal-plan--two-sided`, is not one the cycle explored" in run.err
    run = world.run(
        "review_cycle", FIRST, "--reached", "52", "--evidence", "nothing-like-it", *decision
    )
    assert run.code == 1
    assert "there is no experiment `meal-plan--nothing-like-it`" in run.err
    assert lb.snapshot(world.root) == kept


def test_review_cycle_needs_the_winner_named_where_the_cycle_explored_several(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = in_review(tmp_path, monkeypatch)
    world.edit(lb.CYCLE, lambda data: data["variants"].append("[canvas:meal-plan--two-sided]"))
    run = world.run(
        "review_cycle", FIRST, "--reached", "52", "--decision", "pause", "--reasons", "Stop"
    )
    assert run.code == 1
    assert (
        "the cycle explored `meal-plan--direct`, `meal-plan--two-sided`: name the one that did "
        "best with --winning" in run.err
    )


def test_review_cycle_refuses_a_cycle_not_in_review(
    world: lb.World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decision = ("--reached", "52", "--decision", "pause", "--reasons", "Stop")
    run = world.run("review_cycle", FIRST, *decision)
    assert run.code == 1
    assert f"`{FIRST}` is decided already" in run.err
    planned(world)
    run = world.run("review_cycle", SECOND, "--reached", "3", *decision[2:])
    assert run.code == 1
    assert (
        f"`{SECOND}` is planned, and a cycle is reviewed once its window has ended: its "
        f"window falls 2027-03-10 through 2027-05-08" in run.err
    )
    later = lb.world(tmp_path / "suspended", monkeypatch, date(2027, 2, 28))
    first_only(later, suspended_on_day_50)
    run = later.run("review_cycle", FIRST, *decision)
    assert run.code == 1
    assert f"is suspended: it is resumed first, `pkit lean resume {FIRST}`" in run.err


# --- the briefing -----------------------------------------------------------------------------


def quiet(world: lb.World) -> None:
    """The fixture's cycle running from 2026-11-01, nothing recorded on it since it was
    planned on 2026-10-20: no suspension, no review and no experiment."""
    first_only(world, lambda data: data.pop("suspensions"))


@pytest.mark.parametrize(
    ("day", "offered"),
    [(date(2026, 11, 20), False), (date(2026, 11, 21), True)],
    ids=["after-20-days-none", "after-21-days-offered"],
)
def test_status_offers_to_record_a_silence_of_three_weeks_as_a_suspension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, day: date, offered: bool
) -> None:
    world = lb.world(tmp_path, monkeypatch, day)
    quiet(world)
    idea = briefing(world)
    if not offered:
        assert idea["offer"] is None
        return
    command = (
        f"pkit lean suspend {FIRST} --reason <why> --since 2026-11-01 --resumed <the day you "
        f"came back>"
    )
    assert idea["offer"] == {
        "cycle": FIRST,
        "last_work": "2026-10-20",
        "first_day": "2026-11-01",
        "window_end": "2027-01-29",
        "window_end_if_back_today": "2027-02-18",
        "command": command,
    }
    run = world.run("status", "meal-plan")
    lines = run.out.splitlines()
    assert lines[1:3] == [
        f"  Nothing has been recorded on `{FIRST}` since 2026-10-20. If you were away, the gap "
        f"can be recorded as a suspension from 2026-11-01, which would move the window's end, "
        f"2027-01-29, later by the days you were away: to 2027-02-18, were you back today.",
        f"    {command}",
    ]
    # The offer holds: the suspension it offers is one the command records.
    run = world.run(
        "suspend",
        FIRST,
        "--reason",
        "Away",
        "--since",
        "2026-11-01",
        "--resumed",
        day.isoformat(),
        "--person-decided",
    )
    assert run.code == 0, run.err
    assert briefing(world)["offer"] is None


@pytest.mark.parametrize(
    ("last_work", "offered"),
    [(date(2027, 2, 14), False), (date(2027, 2, 1), False), (date(2027, 1, 22), True)],
    ids=["after-its-window", "11-days-before-its-end", "21-days-before-its-end"],
)
def test_status_counts_only_the_silent_days_within_the_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, last_work: date, offered: bool
) -> None:
    # The cycle in review on 2027-03-20, its window ended on 2027-02-12, nothing recorded
    # on it since a result: the days after its window are no silence of it, so only the
    # days from the result through the window's end count.
    world = lb.world(tmp_path, monkeypatch, date(2027, 3, 20))
    world.edit(lb.CYCLE, lambda data: data.pop("review"))

    def late(data: Any) -> None:
        data["result"]["when"] = last_work
        del data["decision"]

    world.edit(f"{lb.IDEA}/experiments/landing-page.yaml", late)
    idea = briefing(world)
    assert idea["cycles"][0]["state"] == "in-review"
    if not offered:
        assert idea["offer"] is None
        return
    assert (idea["offer"]["last_work"], idea["offer"]["first_day"]) == (
        "2027-01-22",
        "2027-01-23",
    )


def test_status_briefs_a_running_cycle_and_its_experiment_in_full(world: lb.World) -> None:
    declared(world)
    on(world, date(2027, 3, 26))
    run = world.run(
        "record_result",
        DRAFT,
        "--measured",
        "9",
        "--evidence",
        "The call notes",
        "--learned",
        "A weekly call keeps them planning",
        "--person-decided",
    )
    assert run.code == 0, run.err
    on(world, date(2027, 3, 27))
    run = world.run("status", "meal-plan")
    assert run.code == 0, run.err
    assert run.out.splitlines() == [
        "The idea `meal-plan`",
        f"  last act: on 2027-03-26, the result of `{DRAFT}`",
        "  goal: 1000000 EUR a year, within 3 years",
        "  cycles:",
        f"    {FIRST}: decided, persevere for `meal-plan--direct`; window 2026-11-01 through "
        "2027-02-12",
        f"    {SECOND}: running, day 18 of 60; window 2027-03-10 through 2027-05-08",
        "      objective: Show that households keep paying for a planned week",
        "      key result: `meal-plan--direct`, revenue, target 30",
        "      constraint: revenue: Few of those who came back paid",
        "  variants:",
        "    meal-plan--direct: shortlisted",
        "    meal-plan--two-sided: shelved",
        "  experiments:",
        "    meal-plan--first-interviews: decided, double down; its result, a pass",
        f"    {LANDING_PAGE}: decided, double down; its result, a pass",
        f"    {DRAFT}: due; 2027-03-12 through 2027-03-25",
        "      expected: a fit of 8 calls that tell the same story",
        "      result: a pass, measured 9",
        "  waiting on you:",
        f"    {DRAFT}: its result is recorded, and your next action waits",
        f"      pkit lean decide {DRAFT} correct-course|double-down|stop",
    ]
    idea = briefing(world)
    assert idea["last_act"] == {"day": "2027-03-26", "what": [f"the result of `{DRAFT}`"]}
    second = idea["cycles"][1]
    assert second["window"] == {
        "start": "2027-03-10",
        "end": "2027-05-08",
        "days": 60,
        "counted": 18,
    }
    assert second["key_results"] == [
        {"variant": "meal-plan--direct", "metric": "revenue", "target": 30, "reached": None}
    ]
    assert second["review"] is None
    assert idea["experiments"][2] == {
        "id": DRAFT,
        "state": "due",
        "why": None,
        "kind": "generative",
        "cycle": SECOND,
        "time_box": {"start": "2027-03-12", "end": "2027-03-25"},
        "expected": "a fit of 8 calls that tell the same story",
        "outcome": "pass",
    }


def test_status_says_a_result_measured_nothing(world: lb.World) -> None:
    declared(world)
    on(world, date(2027, 3, 26))
    argv = ("--evidence", "The call notes", "--learned", "Too few calls", "--person-decided")
    assert world.run("record_result", DRAFT, *argv).code == 0
    run = world.run("status", "meal-plan")
    assert "      result: neither pass nor fail, nothing measured" in run.out.splitlines()
    assert "None" not in run.out


def test_status_shows_what_waits_in_its_order(
    world: lb.World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # After a persevere, the next cycle waits to be planned; after a pause, nothing waits.
    (waiting,) = briefing(world)["waiting"]
    assert waiting["subject"] == "meal-plan"
    assert waiting["command"].startswith("pkit lean plan-cycle meal-plan--<cycle> --variant")

    def paused(data: Any) -> None:
        data["review"]["decision"] = "pause"

    world.edit(lb.CYCLE, paused)
    assert briefing(world)["waiting"] == []
    # A suspended cycle waits to be resumed, first.
    away = lb.world(tmp_path / "suspended", monkeypatch, date(2027, 2, 28))
    first_only(away, suspended_on_day_50)
    assert [w["command"] for w in briefing(away)["waiting"]] == [
        f"pkit lean resume {FIRST} [--on <day>]"
    ]
    # A cycle in review waits for its review.
    review = in_review(tmp_path / "in-review", monkeypatch)
    assert [w["command"].split(" --")[0] for w in briefing(review)["waiting"]] == [
        f"pkit lean review-cycle {FIRST}"
    ]


def reworded(data: Any) -> None:
    """The direct variant's canvas with its problem reworded since its verdicts."""
    data["boxes"]["problem"][0]["text"] = "Planning the week takes an evening"


def test_status_marks_stale_judgements_and_what_takes_each_again(world: lb.World) -> None:
    world.edit(lb.DIRECT, reworded)
    idea = briefing(world)
    direct = idea["variants"][0]
    stale = direct["stale"]
    assert "desirability" in stale
    assert stale[-1] == "shortlisting"
    commands = [w["command"] for w in idea["waiting"]]
    assert commands == [
        *(f"pkit lean judge meal-plan--direct {step} yes|no" for step in stale[:-1]),
        "pkit lean shortlist meal-plan--direct",
    ]
    run = world.run("status", "meal-plan")
    assert f"    meal-plan--direct: shortlisted; stale: {', '.join(stale)}" in run.out


def test_status_lists_a_stale_verdict_on_the_step_judged_next_once(world: lb.World) -> None:
    # A no on desirability leaves the variant sketched, with desirability judged next; an
    # entry added since makes that no stale, and one command takes both.
    variant = "meal-plan--boxes"
    assert world.run("new_variant", variant, "--archetype", "direct").code == 0
    run = world.run("judge", variant, "desirability", "no", "--person-decided")
    assert run.code == 0, run.err
    assert world.run("add_entry", variant, "problem", "Recipes run out").code == 0
    idea = briefing(world)
    assert [v["stale"] for v in idea["variants"] if v["id"] == variant] == [["desirability"]]
    waiting = [w for w in idea["waiting"] if w["subject"] == variant]
    assert waiting == [
        {
            "subject": variant,
            "what": "its verdict on desirability is stale: what it judged changed since",
            "command": f"pkit lean judge {variant} desirability yes|no",
        }
    ]


def test_status_marks_nothing_judged_against_a_goal_that_does_not_read_stale(
    world: lb.World,
) -> None:
    # Whether a verdict judged against the goal, or the shortlisting, is stale cannot be
    # told while the goal's file does not read, so the briefing marks none, as the check
    # marks none. Desirability is judged without the goal.
    world.edit(lb.DIRECT, reworded)
    (world.root / lb.GOAL).write_text("revenue: [unclosed\n", encoding="utf-8")
    idea = briefing(world)
    assert idea["variants"][0]["stale"] == ["desirability"]
    assert [w["command"] for w in idea["waiting"]] == [
        "pkit lean judge meal-plan--direct desirability yes|no"
    ]
    run = world.run("status", "meal-plan")
    assert "    meal-plan--direct: shortlisted; stale: desirability" in run.out.splitlines()


def test_status_says_the_goal_cannot_be_read_where_its_file_does_not_read(
    world: lb.World,
) -> None:
    (world.root / lb.GOAL).write_text("revenue: [unclosed\n", encoding="utf-8")
    why = f"the idea's goal at `{lb.GOAL}` cannot be read"
    idea = briefing(world)
    assert (idea["goal"], idea["goal_why"]) == (None, why)
    run = world.run("status", "meal-plan")
    assert f"  goal: {why}" in run.out.splitlines()
    run = world.run("status")
    assert run.out.startswith("meal-plan: a goal whose file cannot be read, 2 variants")


def test_status_gives_null_for_a_goal_value_that_does_not_read(world: lb.World) -> None:
    def misshapen(data: Any) -> None:
        data["years"] = "ten"
        data["revenue"]["per"] = 12

    world.edit(lb.GOAL, misshapen)
    idea = briefing(world)
    assert idea["goal"] == {"revenue": 1000000, "per": None, "currency": "EUR", "years": None}
    run = world.run("status", "meal-plan")
    assert "  goal: set, but its period and years cannot be read" in run.out.splitlines()


def test_status_lists_a_cycle_and_an_experiment_whose_file_does_not_read(
    world: lb.World,
) -> None:
    # Each stays in the briefing, where it stands cannot be told, and what its file would
    # say is null. A cycle that cannot be read counts as undecided, so no next cycle waits
    # to be planned.
    (world.root / lb.CYCLE).write_text("id: [unclosed\n", encoding="utf-8")
    (world.root / lb.IDEA / "experiments/landing-page.yaml").write_text(
        "id: [unclosed\n", encoding="utf-8"
    )
    idea = briefing(world)
    (cycle,) = idea["cycles"]
    assert cycle["id"] == FIRST and cycle["why"], cycle
    assert {key: value for key, value in cycle.items() if key not in ("id", "why")} == (
        dict.fromkeys(
            ("state", "window", "objective", "key_results", "constraint", "suspensions", "review")
        )
    )
    (landing,) = (e for e in idea["experiments"] if e["id"] == LANDING_PAGE)
    assert landing["why"], landing
    assert {key: value for key, value in landing.items() if key not in ("id", "why")} == (
        dict.fromkeys(("state", "kind", "cycle", "time_box", "expected", "outcome"))
    )
    assert idea["waiting"] == []
    shown = world.run("status", "meal-plan").out.splitlines()
    assert f"    {FIRST}: cannot be told: {cycle['why']}" in shown
    assert f"    {LANDING_PAGE}: cannot be told: {landing['why']}" in shown
    every = world.run("status").out.splitlines()
    (line,) = (each for each in every if each.startswith("meal-plan"))
    assert "waiting" not in line
