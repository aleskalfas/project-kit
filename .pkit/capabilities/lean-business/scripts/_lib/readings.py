"""What follows from an idea's files, worked out each time it is read and never stored
(lean-business DEC-002 point 2).

- **Priced** (`priced`): a canvas whose revenue streams hold an entry. The viability gate
  needs it, and the check warns on a canvas without it once its desirability has a yes, so
  the two read this one predicate (DEC-002 point 14, DEC-003 point 2).
- **The standing verdicts** (`standing`): the longest run of standing yes verdicts from the
  first desk step, which is where the desk stage reads a variant to stand before its
  outcome (DEC-003 point 2).
- **An experiment's pass or fail** (`experiment_outcome`), compared from the recorded result
  and the declared expectation, never stored or asserted (DEC-002 point 10).
- **Whether a variant met its cycle's objective** (`met_objective`), from the targets of the
  key results that name it and what its review says they reached (DEC-002 point 11).
- **An assumption's outcome** (`assumption_outcome`), from the experiments that test it
  (DEC-003 point 8).
- **An idea dropped** (`dropped`), from its variants' outcomes (DEC-003 point 8).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from _lib import ids
from _lib.fingerprint import STEPS
from _lib.reading import day

#: What an experiment's result works out to.
PASS = "pass"
FAIL = "fail"
NEITHER = "neither"

#: An assumption's outcome (DEC-003 point 8).
UNTESTED = "untested"
BEING_TESTED = "being-tested"
SUPPORTED = "supported"
REFUTED = "refuted"
INCONCLUSIVE = "inconclusive"

#: The outcome each result works out to gives the assumption it tested.
_FROM_RESULT = {PASS: SUPPORTED, FAIL: REFUTED, NEITHER: INCONCLUSIVE}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def entries(canvas: Mapping[str, Any], box: str) -> list[Mapping[str, Any]]:
    """The entries a canvas's `box` holds that read as entries."""
    found = _mapping(canvas.get("boxes")).get(box)
    return (
        [entry for entry in found if isinstance(entry, Mapping)] if isinstance(found, list) else []
    )


def priced(canvas: Mapping[str, Any]) -> bool:
    """Whether the canvas prices its model: its revenue streams hold an entry."""
    return bool(entries(canvas, "revenue-streams"))


def answer(canvas: Mapping[str, Any], step: str) -> str | None:
    """The person's answer on `step`, `yes` or `no`, or None where no verdict stands."""
    verdict = _mapping(_mapping(canvas.get("verdicts")).get(step))
    found = verdict.get("answer")
    return found if found in ("yes", "no") else None


def standing(canvas: Mapping[str, Any]) -> tuple[str, ...]:
    """The steps the person's yes stands on, each with a yes on every step before it: the
    longest run of yes verdicts from the first step."""
    run: list[str] = []
    for step in STEPS:
        if answer(canvas, step) != "yes":
            break
        run.append(step)
    return tuple(run)


def experiment_outcome(experiment: Mapping[str, Any]) -> str | None:
    """What an experiment's result works out to, `PASS`, `FAIL` or `NEITHER`, or None where
    no result is recorded.

    - Evaluative, a threshold: it passes where the result reaches the threshold in the
      declared direction.
    - Evaluative, a range: it passes where the result reaches the range's low for
      `at-least`, or stays within its high for `at-most`.
    - Generative: it passes where the result reaches the count that counts as fit, and
      fails where the stopping rule was reached without it.
    - Neither where the comparison cannot be made: nothing measured, a measurement the
      person recorded as spoiled, a generative experiment whose time box ended below its
      fit and before its stopping rule, or an expectation that cannot be read.
    """
    result = experiment.get("result")
    if not isinstance(result, Mapping):
        return None
    measured = _number(result.get("measured"))
    if measured is None or result.get("spoiled") is True:
        return NEITHER
    if experiment.get("kind") == "generative":
        fit = _number(_mapping(experiment.get("fit")).get("count"))
        if fit is None:
            return NEITHER
        if measured >= fit:
            return PASS
        return FAIL if isinstance(experiment.get("stopped"), Mapping) else NEITHER
    if experiment.get("kind") == "evaluative":
        return _evaluative(_mapping(experiment.get("expected")), measured)
    return NEITHER


def _evaluative(expected: Mapping[str, Any], measured: float) -> str:
    direction = expected.get("direction")
    threshold = _number(expected.get("threshold"))
    span = _mapping(expected.get("range"))
    if direction == "at-least":
        bound = threshold if threshold is not None else _number(span.get("low"))
        if bound is None:
            return NEITHER
        return PASS if measured >= bound else FAIL
    if direction == "at-most":
        bound = threshold if threshold is not None else _number(span.get("high"))
        if bound is None:
            return NEITHER
        return PASS if measured <= bound else FAIL
    return NEITHER


def key_results_of(cycle: Mapping[str, Any], variant: str) -> list[tuple[int, Mapping[str, Any]]]:
    """The key results of a cycle's objective that name `variant`, a variant's id, each with
    its place in the objective's list."""
    found = _mapping(cycle.get("objective")).get("key-results")
    if not isinstance(found, list):
        return []
    named: list[tuple[int, Mapping[str, Any]]] = []
    for index, result in enumerate(found):
        if not isinstance(result, Mapping):
            continue
        reference = ids.parse_ref(result.get("variant"), ids.CANVAS)
        if reference is not None and reference.id == variant:
            named.append((index, result))
    return named


def met_objective(cycle: Mapping[str, Any], variant: str) -> bool | None:
    """Whether `variant`, a variant's id, met its cycle's objective: each key result that
    names it reached its target, by what the cycle's review records. None where the cycle
    has no review, names no key result of the variant, or its review records no reach for
    one of them."""
    review = cycle.get("review")
    if not isinstance(review, Mapping):
        return None
    reached = review.get("reached")
    named = key_results_of(cycle, variant)
    if not named or not isinstance(reached, Sequence) or isinstance(reached, str):
        return None
    met = True
    for index, result in named:
        target = _number(result.get("target"))
        value = _number(reached[index]) if index < len(reached) else None
        if target is None or value is None:
            return None
        met = met and value >= target
    return met


def assumption_outcome(assumption: str, experiments: Iterable[Mapping[str, Any]]) -> str:
    """The outcome of the assumption `assumption`, an assumption's id, from `experiments`,
    the files of its idea's experiments (DEC-003 point 8):

    - `UNTESTED` while no declared experiment names it, a draft being no test;
    - `BEING_TESTED` while one that names it is declared and not decided, that is declared,
      running or due;
    - otherwise what the one decided last gives: `SUPPORTED` where it passed, `REFUTED`
      where it failed, `INCONCLUSIVE` where it worked out to neither.

    Days have no order within them, so of experiments decided on the same last day the one
    whose id sorts last counts, which keeps the reading the same each time it is made. A
    decision whose day cannot be read counts as the earliest."""
    decided: list[tuple[date, str, Mapping[str, Any]]] = []
    for experiment in experiments:
        named = ids.parse_ref(experiment.get("assumption"), ids.ASSUMPTIONS)
        if named is None or named.id != assumption:
            continue
        if not isinstance(experiment.get("declared"), Mapping):
            continue
        decision = experiment.get("decision")
        if not isinstance(decision, Mapping):
            return BEING_TESTED
        when = day(decision.get("when")) or date.min
        decided.append((when, str(experiment.get("id", "")), experiment))
    if not decided:
        return UNTESTED
    *_, last = max(decided, key=lambda each: (each[0], each[1]))
    return _FROM_RESULT[experiment_outcome(last) or NEITHER]


def dropped(canvases: Iterable[Mapping[str, Any]]) -> bool:
    """Whether an idea is dropped, from its variants' canvases: it has a variant, and every
    variant that was not split is shelved (DEC-003 point 8). Dropping is no move of its own,
    but what shelving its last variant leaves."""
    kinds = [_mapping(canvas.get("outcome")).get("kind") for canvas in canvases]
    return bool(kinds) and all(kind == "shelved" for kind in kinds if kind != "split")
