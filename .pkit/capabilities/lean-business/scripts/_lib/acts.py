"""The acts recorded in an idea's files, each with the gate that judges it (lean-business
DEC-002 points 12 and 14; DEC-003 points 3 and 4).

An *act* is a judgement or an act of the person's recorded with its day: the goal set; a
cycle's first planning, the last change to its plan and its review; and an experiment's
declaration, stopping rule reached, result and decision. Each carries its gate (`gates`),
asked with the act's day and with each cycle the gate reads as a *view* gives it: the
cycle's data, as its suspensions stood (`timeline.stood`).

- **The check** asks each act with every cycle as its suspensions stood on the act's day
  (`as_stood`).
- **A suspension's rules** ask each act recorded by the day the suspension was recorded
  with the suspension and without it, so a suspension recorded late contradicts no act
  already recorded (`suspensions`). The command that records a suspension asks each act
  with the new one and without it, through the same rules.

So the check, a suspension's rules and the commands ask one gate of each act, and never
disagree on it. A suspension's own recording and its resumption are no acts here: the
suspension rules read the suspensions themselves.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from _lib import fingerprint, gates, ids, model, timeline
from _lib.findings import at
from _lib.gates import Refusal
from _lib.model import Cycle, Experiment, IdeaModel, found
from _lib.reading import day

#: A cycle's data as a reader gives it to a gate: as it stands, or as its suspensions
#: stood on a day.
View = Callable[[Mapping[str, Any]], Mapping[str, Any]]

#: How an act's gate is asked: with the view of each cycle it reads.
Ask = Callable[[View], list[Refusal]]

#: The gates of what is recorded on an experiment after its declaration, by the key it is
#: recorded at, each with what it is in words and the label the check reports it with.
AFTER_DECLARED: tuple[tuple[str, str, Callable[..., list[Refusal]], str], ...] = (
    ("stopped", "the stopping rule reached", gates.stopping, "stop-refused"),
    ("result", "the result", gates.result, "result-refused"),
    ("decision", "the decision", gates.deciding, "decision-refused"),
)


@dataclass(frozen=True)
class Act:
    """An act recorded on `day`: what it was, in words; the file it is recorded in and the
    place within it; the label the check reports a refusal of its gate with; and how its
    gate is asked, where one judges it."""

    day: date
    what: str
    rel: str = ""
    pointer: str = ""
    label: str = ""
    ask: Ask | None = None

    @property
    def where(self) -> str:
        """Where the act is recorded: its file, and the place within it."""
        return at(self.rel, self.pointer)


def as_stood(act: Act) -> list[Refusal]:
    """Why `act`'s gate refuses it, asked with each cycle as its suspensions stood on the
    act's day. None where the gate lets it through once the suspensions recorded that same
    day are left out: days have no order within them, so such a suspension may have come
    after the act, and the suspension's rules report the break at it (`suspensions`)."""
    if act.ask is None:
        return []
    refused = act.ask(lambda cycle: timeline.stood(cycle, act.day))
    if refused and not act.ask(lambda cycle: timeline.stood(cycle, act.day, _not_on(act.day))):
        return []
    return refused


def _not_on(when: date) -> Callable[[timeline.Suspension], bool]:
    """Keeps each suspension but those recorded on `when`."""
    return lambda suspension: suspension.recorded != when


# --- the acts of an idea --------------------------------------------------------------------------


def recorded(idea: IdeaModel) -> list[Act]:
    """Every act recorded in the idea's files: the goal set, each cycle's and each
    experiment's."""
    found_acts = of_goal(idea)
    for cycle in idea.cycles:
        found_acts.extend(of_cycle(idea, cycle))
    for experiment in idea.experiments:
        found_acts.extend(of_experiment(idea, experiment))
    return found_acts


def bearing_on(idea: IdeaModel, cycle: Cycle) -> list[Act]:
    """The acts a cycle's suspensions bear on: those recorded on the cycle and on its
    experiments, and the goal set, which a planned, running or suspended cycle holds
    still (DEC-002 points 3 and 12)."""
    cycle_id = cycle.data.get("id")
    experiments = idea.experiments_of(cycle_id) if isinstance(cycle_id, str) else []
    found_acts = of_cycle(idea, cycle)
    for experiment in experiments:
        found_acts.extend(of_experiment(idea, experiment))
    return [*found_acts, *of_goal(idea)]


def of_goal(idea: IdeaModel) -> list[Act]:
    """The goal set, judged by `gates.setting_goal` over every cycle of the idea. The
    files keep no goal it replaced, so its currency is the command's alone to judge."""
    goal_file, goal = idea.idea.goal, idea.goal
    on = day(goal.get("when")) if goal is not None else None
    if goal_file is None or goal is None or on is None:
        return []
    cycles = [cycle.data for cycle in idea.cycles]

    def ask(view: View) -> list[Refusal]:
        return gates.setting_goal(goal, on, cycles=[view(cycle) for cycle in cycles])

    return [Act(on, "the goal set", goal_file.rel, "", "goal-changed", ask)]


def of_cycle(idea: IdeaModel, cycle: Cycle) -> list[Act]:
    """The acts recorded on a cycle: its first planning, judged by `gates.planning`; the
    last change to its plan, where it fell on a later day, by `gates.changing`; and its
    review, by `gates.deciding_cycle`."""
    data, rel = cycle.data, cycle.rel
    named = data.get("id", cycle.own)
    found_acts: list[Act] = []
    first = model.first_planned(data)
    if first is not None:
        others = [other.data for other in idea.cycles if other is not cycle]
        goal = idea.goal_for_gates()

        def plan(view: View) -> list[Refusal]:
            return gates.planning(data, first, goal=goal, others=others)

        found_acts.append(
            Act(
                first,
                f"the first planning of `{named}`",
                rel,
                "/planned/first",
                "plan-refused",
                plan,
            )
        )
    last = day(_m(data.get("planned")).get("when"))
    if last is not None and last != first:

        def change(view: View) -> list[Refusal]:
            return gates.changing(view(data), last)

        found_acts.append(
            Act(
                last,
                f"the last change to the plan of `{named}`",
                rel,
                "/planned",
                "plan-refused",
                change,
            )
        )
    review = _m(data.get("review"))
    decided = day(review.get("when"))
    if decided is not None:
        winning = found(idea.resolve(review.get("winning"), ids.CANVAS))
        cited = [found(idea.resolve(v, ids.EXPERIMENT)) for v in _list(review.get("evidence"))]
        evidence = [experiment for experiment in cited if experiment is not None]

        def decide(view: View) -> list[Refusal]:
            return gates.deciding_cycle(view(data), decided, winning=winning, evidence=evidence)

        found_acts.append(
            Act(decided, f"the review of `{named}`", rel, "/review", "review-refused", decide)
        )
    return found_acts


def of_experiment(idea: IdeaModel, experiment: Experiment) -> list[Act]:
    """The acts recorded on an experiment, each judged under the cycle it names: its
    declaration, by `gates.declaring` with the shortlisting the declaration records; and its
    stopping rule reached, its result and its decision, by `gates.stopping`, `gates.result`
    and `gates.deciding`. On an experiment never declared these three take no gate, since
    the check reports each as recorded on an experiment never declared."""
    data, rel = experiment.data, experiment.rel
    named = data.get("id", experiment.own)
    cycle = found(idea.cycle_of(experiment))
    declared = model.declared(data)
    found_acts: list[Act] = []
    on = day(_m(data.get("declared")).get("when"))
    if declared and on is not None:
        found_acts.append(
            Act(
                on,
                f"the declaration of `{named}`",
                rel,
                "/declared",
                "declaration-refused",
                _declaring(idea, experiment, on, cycle),
            )
        )
    for key, what, gate, label in AFTER_DECLARED:
        when = day(_m(data.get(key)).get("when"))
        if when is None:
            continue
        ask = _after(gate, data, when, cycle) if declared else None
        found_acts.append(Act(when, f"{what} of `{named}`", rel, f"/{key}", label, ask))
    return found_acts


def _declaring(
    idea: IdeaModel, experiment: Experiment, on: date, cycle: Mapping[str, Any] | None
) -> Ask:
    """How the declaring gate is asked of a declaration recorded on `on`: on the canvas of
    the variant it tests, resting on the shortlisting it recorded. Where that shortlisting
    does not read whole, which the shape, or the day, reports, what it rested on cannot be
    told, so the gate is given no canvas."""
    data = experiment.data
    variant = idea.variant_tested(experiment)
    canvas = found(idea.canvas_of(variant)) if variant else None
    written = _m(data.get("declared")).get("rested-on")
    rests_on = fingerprint.rested_on(written)
    if written is not None and rests_on is None:
        canvas = None

    def ask(view: View) -> list[Refusal]:
        seen = view(cycle) if cycle is not None else None
        return gates.declaring(data, on, cycle=seen, canvas=canvas, rests_on=rests_on)

    return ask


def _after(
    gate: Callable[..., list[Refusal]],
    experiment: Mapping[str, Any],
    on: date,
    cycle: Mapping[str, Any] | None,
) -> Ask:
    """How `gate`, of what is recorded on an experiment after its declaration, is asked of
    what was recorded on `on`."""

    def ask(view: View) -> list[Refusal]:
        return gate(experiment, on, view(cycle) if cycle is not None else None)

    return ask


def _m(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []
