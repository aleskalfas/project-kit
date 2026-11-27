"""The acts recorded in a lean-business idea's files, each with the gate that judges it, which
the check and a suspension's rules ask alike (DEC-002 points 3, 12 and 14; DEC-003 points 3
and 4)."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Any

from tests.in_process import load

(acts, gates, layout, model, timeline) = load(
    "lean-business", "acts", "gates", "layout", "model", "timeline"
)

FIXTURE = Path(__file__).resolve().parent / "fixtures/lean-business/.repo"
IDEA = "lean-business/meal-plan"
CYCLE = f"{IDEA}/cycles/first.yaml"
INTERVIEWS = f"{IDEA}/experiments/first-interviews.yaml"
LANDING = f"{IDEA}/experiments/landing-page.yaml"


def idea_model(tmp_path: Path) -> Any:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    contents = layout.read(root, "lean-business")
    return model.IdeaModel(contents.ideas["meal-plan"], model.Pools.of(contents))


# --- the acts of an idea ------------------------------------------------------------------------


def test_every_act_recorded_in_the_ideas_files_with_its_gate(tmp_path: Path) -> None:
    recorded = acts.recorded(idea_model(tmp_path))
    assert [(act.day.isoformat(), act.where, act.label) for act in recorded] == [
        ("2026-10-01", f"{IDEA}/goal.yaml", "goal-changed"),
        ("2026-10-20", f"{CYCLE}#/planned/first", "plan-refused"),
        ("2027-02-15", f"{CYCLE}#/review", "review-refused"),
        ("2026-11-02", f"{INTERVIEWS}#/declared", "declaration-refused"),
        ("2026-11-17", f"{INTERVIEWS}#/result", "result-refused"),
        ("2026-11-17", f"{INTERVIEWS}#/decision", "decision-refused"),
        ("2026-12-10", f"{LANDING}#/declared", "declaration-refused"),
        ("2027-01-04", f"{LANDING}#/result", "result-refused"),
        ("2027-01-05", f"{LANDING}#/decision", "decision-refused"),
    ]
    assert all(act.ask is not None for act in recorded)
    assert all(acts.as_stood(act) == [] for act in recorded)


def test_the_acts_a_cycles_suspensions_bear_on(tmp_path: Path) -> None:
    idea = idea_model(tmp_path)
    [cycle] = idea.cycles
    bearing = acts.bearing_on(idea, cycle)
    assert [act.what for act in bearing] == [
        "the first planning of `meal-plan--first`",
        "the review of `meal-plan--first`",
        "the declaration of `meal-plan--first-interviews`",
        "the result of `meal-plan--first-interviews`",
        "the decision of `meal-plan--first-interviews`",
        "the declaration of `meal-plan--landing-page`",
        "the result of `meal-plan--landing-page`",
        "the decision of `meal-plan--landing-page`",
        "the goal set",
    ]


def test_what_is_recorded_on_an_experiment_never_declared_takes_no_gate(tmp_path: Path) -> None:
    idea = idea_model(tmp_path)
    interviews = idea.experiments[0]
    undeclared = model.Experiment(
        interviews.rel,
        interviews.own,
        {k: v for k, v in interviews.data.items() if k != "declared"},
    )
    found = acts.of_experiment(idea, undeclared)
    assert [(act.pointer, act.ask) for act in found] == [("/result", None), ("/decision", None)]


# --- as the suspensions stood on the act's day --------------------------------------------------


def window_ended_by(cycle: dict[str, Any], day: date) -> Any:
    """An act on `day` refused while `cycle`'s window, as the view gives it, has not ended."""

    def ask(view: Any) -> list[Any]:
        span = timeline.cycle_window(view(cycle))
        if span is None or span.end is None or span.end >= day:
            return [gates.Refusal("", "the window has not ended")]
        return []

    return acts.Act(day, "the review", "c.yaml", "/review", "review-refused", ask)


def thirty_days(recorded: str) -> dict[str, Any]:
    """A cycle whose window runs from 2026-12-01 through 2026-12-30, before one suspension
    recorded on `recorded` that moves its end to 2027-01-01."""
    return {
        "window": {"start": "2026-12-01", "days": 30},
        "suspensions": [
            {
                "first-day": "2026-12-10",
                "when": recorded,
                "resumed": {"day": "2026-12-12", "when": recorded},
            }
        ],
    }


def test_an_act_is_asked_with_the_suspensions_recorded_by_its_day() -> None:
    assert acts.as_stood(window_ended_by(thirty_days("2026-12-12"), date(2026, 12, 31)))
    assert acts.as_stood(window_ended_by(thirty_days("2027-01-02"), date(2026, 12, 31))) == []


def test_an_act_passed_without_the_suspensions_of_its_own_day_is_theirs_to_answer() -> None:
    # Days have no order within them: the suspension may have come after the act, and its
    # rules report the break at it.
    assert acts.as_stood(window_ended_by(thirty_days("2026-12-31"), date(2026, 12, 31))) == []


# --- the goal set -------------------------------------------------------------------------------


GOAL = {"revenue": {"amount": 1000000, "per": "year"}, "currency": "EUR", "years": 3}

RUNNING = {
    "id": "idea--first",
    "window": {"start": "2026-12-01", "days": 30},
    "planned": {"first": {"when": "2026-11-20"}, "when": "2026-11-20"},
}


def test_the_goal_is_set_only_while_no_cycle_is_planned_running_or_suspended() -> None:
    for on in (date(2026, 11, 21), date(2026, 12, 30)):
        [refused] = gates.setting_goal(GOAL, on, cycles=[RUNNING])
        assert "while the cycle `idea--first` was planned, running or suspended" in (
            refused.message
        )
    for on in (date(2026, 11, 20), date(2026, 12, 31)):
        assert gates.setting_goal(GOAL, on, cycles=[RUNNING]) == []


DECLARED = {"id": "idea--landing", "declared": {"when": "2026-10-10"}}


def test_its_currency_changes_only_while_no_declared_experiment_is_undecided() -> None:
    on = date(2026, 11, 1)
    changed = {**GOAL, "currency": "USD"}
    [refused] = gates.setting_goal(changed, on, cycles=[], previous=GOAL, experiments=[DECLARED])
    assert refused.pointer == "/currency"
    assert "from EUR to USD" in refused.message and "`idea--landing`" in refused.message
    decided = {**DECLARED, "decision": {"when": "2026-10-30"}}
    assert gates.setting_goal(changed, on, cycles=[], previous=GOAL, experiments=[decided]) == []
    later = {**DECLARED, "declared": {"when": "2026-11-02"}}
    assert gates.setting_goal(changed, on, cycles=[], previous=GOAL, experiments=[later]) == []
    # The same currency, or a goal set the first time, asks nothing of the experiments.
    years = {**GOAL, "years": 5}
    assert gates.setting_goal(years, on, cycles=[], previous=GOAL, experiments=[DECLARED]) == []
    assert gates.setting_goal(changed, on, cycles=[], experiments=[DECLARED]) == []
