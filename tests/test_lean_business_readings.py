"""What lean-business works out from an idea's files and never stores (DEC-002 points 2, 10
and 11): pricing, the standing verdicts, an experiment's pass or fail, and whether a variant
met its cycle's objective."""

from __future__ import annotations

from typing import Any

import pytest

from tests.in_process import load

(readings,) = load("lean-business", "readings")


def evaluative(direction: str, **expected: Any) -> dict[str, Any]:
    return {"kind": "evaluative", "expected": {"direction": direction, **expected}}


def measured(experiment: dict[str, Any], value: Any, **result: Any) -> dict[str, Any]:
    return {**experiment, "result": {"measured": value, **result}}


# --- pricing and the verdicts -------------------------------------------------------------------


def test_a_canvas_is_priced_once_its_revenue_streams_hold_an_entry() -> None:
    assert not readings.priced({})
    assert not readings.priced({"boxes": {"revenue-streams": []}})
    assert not readings.priced({"boxes": {"revenue-streams": ["not an entry"]}})
    assert readings.priced({"boxes": {"revenue-streams": [{"id": "i.v.s", "text": "Fees"}]}})


def test_the_standing_verdicts_are_the_run_of_yes_from_the_first_step() -> None:
    def judged(**answers: str) -> dict[str, Any]:
        return {"verdicts": {step: {"answer": answer} for step, answer in answers.items()}}

    assert readings.standing({}) == ()
    assert readings.standing(judged(desirability="yes")) == ("desirability",)
    assert readings.standing(judged(desirability="yes", viability="no")) == ("desirability",)
    assert readings.standing(judged(viability="yes", feasibility="yes")) == ()
    every = judged(desirability="yes", viability="yes", feasibility="yes")
    assert readings.standing(every) == ("desirability", "viability", "feasibility")
    assert readings.answer(judged(desirability="maybe"), "desirability") is None


# --- an experiment's pass or fail ---------------------------------------------------------------


def test_no_result_is_no_outcome() -> None:
    assert readings.experiment_outcome(evaluative("at-least", threshold=1)) is None


@pytest.mark.parametrize(
    ("direction", "value", "outcome"),
    [
        ("at-least", 5, "pass"),
        ("at-least", 4.9, "fail"),
        ("at-most", 5, "pass"),
        ("at-most", 6, "fail"),
    ],
)
def test_a_threshold_passes_where_it_is_reached_in_its_direction(
    direction: str, value: float, outcome: str
) -> None:
    experiment = measured(evaluative(direction, threshold=5), value)
    assert readings.experiment_outcome(experiment) == outcome


@pytest.mark.parametrize(
    ("direction", "value", "outcome"),
    [
        ("at-least", 3, "pass"),
        ("at-least", 9, "pass"),
        ("at-least", 2, "fail"),
        ("at-most", 8, "pass"),
        ("at-most", 1, "pass"),
        ("at-most", 9, "fail"),
    ],
)
def test_a_range_passes_from_its_low_or_within_its_high(
    direction: str, value: float, outcome: str
) -> None:
    experiment = measured(evaluative(direction, range={"low": 3, "high": 8}), value)
    assert readings.experiment_outcome(experiment) == outcome


def test_a_generative_experiment_passes_at_its_fit_and_fails_where_its_rule_stopped_it() -> None:
    generative = {"kind": "generative", "fit": {"count": 8}}
    assert readings.experiment_outcome(measured(generative, 8)) == "pass"
    stopped = {**generative, "stopped": {"by": "A", "when": "2026-12-05"}}
    assert readings.experiment_outcome(measured(stopped, 5)) == "fail"
    assert readings.experiment_outcome(measured(generative, 5)) == "neither"


@pytest.mark.parametrize(
    "experiment",
    [
        measured(evaluative("at-least", threshold=1), None),
        measured(evaluative("at-least", threshold=1), 3, spoiled=True),
        measured(evaluative("sideways", threshold=1), 3),
        measured(evaluative("at-least"), 3),
        measured({"kind": "generative"}, 3),
        measured({"kind": "other"}, 3),
        measured(evaluative("at-least", threshold=1), True),
    ],
    ids=["nothing-measured", "spoiled", "no-direction", "no-bound", "no-fit", "no-kind", "a-flag"],
)
def test_neither_where_the_comparison_cannot_be_made(experiment: dict[str, Any]) -> None:
    assert readings.experiment_outcome(experiment) == "neither"


# --- the objective ------------------------------------------------------------------------------

DIRECT = "[canvas:idea.direct]"
SIDED = "[canvas:idea.sided]"


def cycle(*reached: Any) -> dict[str, Any]:
    return {
        "objective": {
            "key-results": [
                {"variant": DIRECT, "metric": "retention", "target": 40},
                {"variant": SIDED, "metric": "acquisition", "target": 100},
                {"variant": DIRECT, "metric": "revenue", "target": 10},
            ]
        },
        "review": {"reached": list(reached)},
    }


def test_a_variant_met_the_objective_where_each_of_its_key_results_reached_its_target() -> None:
    assert readings.met_objective(cycle(40, 0, 10), "idea.direct") is True
    assert readings.met_objective(cycle(40, 0, 9), "idea.direct") is False
    assert readings.met_objective(cycle(40, 0, 9), "idea.sided") is False
    assert readings.met_objective(cycle(0, 100, 0), "idea.sided") is True


def test_whether_it_met_the_objective_is_unknown_without_a_review_or_a_reach() -> None:
    assert readings.met_objective({**cycle(), "review": None}, "idea.direct") is None
    assert readings.met_objective(cycle(40, 0), "idea.direct") is None
    assert readings.met_objective(cycle(40, 0, 10), "idea.other") is None
    assert [i for i, _ in readings.key_results_of(cycle(), "idea.direct")] == [0, 2]
