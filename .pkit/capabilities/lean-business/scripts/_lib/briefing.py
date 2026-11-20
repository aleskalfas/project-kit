"""The status of the ideas: where each idea and each of its subjects stands, and what waits
on the person (lean-business DEC-001 point 10; DEC-002 point 15).

It is worked out from the files each time it is shown and kept nowhere. Each subject's
position is the process engine's (`engine`), never worked out here again. Without an
idea, the status gives one line for each idea; with one, its goal, each subject with where
it stands, and what waits on the person, each with the command that takes it.

**Its structured form** (`document`) is a contract its readers depend on (ADR-097): the
capability's README lists its keys. It carries `schema_version`; a change that would break
a reader raises it, and an added key leaves it.

This first status covers the desk: what waits on the person is a goal to set, a step to
judge or a variant to shortlist. The full briefing adds the rest.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from _lib import engine as engines
from _lib import ids, layout, positions
from _lib.engine import Engine, EngineFailed
from _lib.fingerprint import STEPS

#: The version of the structured form.
SCHEMA_VERSION = 1

#: The step judged next in each state of the desk stage that judges one.
NEXT_STEP = {
    positions.SKETCHED: STEPS[0],
    positions.DESIRABLE: STEPS[1],
    positions.VIABLE: STEPS[2],
}


@dataclass(frozen=True)
class Standing:
    """Where a subject stands: its id, its state or None, and why where the engine could
    not tell."""

    id: str
    state: str | None
    why: str = ""

    def as_data(self) -> dict[str, Any]:
        return {"id": self.id, "state": self.state, "why": self.why or None}


@dataclass(frozen=True)
class Waiting:
    """Something that waits on the person: what it is, and the command that takes it."""

    subject: str
    what: str
    command: str

    def as_data(self) -> dict[str, Any]:
        return {"subject": self.subject, "what": self.what, "command": self.command}


@dataclass
class IdeaStatus:
    """An idea's status: its goal, each subject with where it stands, and what waits."""

    id: str
    goal: Mapping[str, Any] | None
    variants: list[Standing] = field(default_factory=list)
    cycles: list[Standing] = field(default_factory=list)
    experiments: list[Standing] = field(default_factory=list)
    waiting: list[Waiting] = field(default_factory=list)

    def as_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": _goal_data(self.goal),
            "variants": [v.as_data() for v in self.variants],
            "cycles": [c.as_data() for c in self.cycles],
            "experiments": [e.as_data() for e in self.experiments],
            "waiting": [w.as_data() for w in self.waiting],
        }


def _goal_data(goal: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if goal is None:
        return None
    revenue = goal.get("revenue") if isinstance(goal.get("revenue"), Mapping) else {}
    return {
        "revenue": revenue.get("amount"),
        "per": revenue.get("per"),
        "currency": goal.get("currency"),
        "years": goal.get("years"),
    }


def _standing(engine: Engine, process: str, subject: str) -> Standing:
    try:
        found = engine.status(process, subject)
    except EngineFailed as exc:
        return Standing(subject, None, str(exc))
    if found.indeterminate:
        return Standing(subject, None, found.why or "the engine cannot tell")
    return Standing(subject, found.state)


def of_idea(engine: Engine, idea: layout.Idea) -> IdeaStatus:
    """The status of `idea`, each subject's position asked of `engine`."""
    goal = idea.goal.data if idea.goal is not None else None
    found = IdeaStatus(idea.name, goal)
    for own in sorted(idea.variants):
        found.variants.append(_standing(engine, engines.DESK, ids.qualify(idea.name, own)))
    for own in sorted(idea.cycles):
        found.cycles.append(_standing(engine, engines.CYCLE, ids.qualify(idea.name, own)))
    for own in sorted(idea.experiments):
        found.experiments.append(_standing(engine, engines.EXPERIMENT, ids.qualify(idea.name, own)))
    if goal is None:
        found.waiting.append(
            Waiting(
                idea.name,
                "the idea has no goal, which viability and feasibility are judged against",
                f"pkit lean set-goal {idea.name} --revenue <amount> --per month|year "
                f"--currency <code> --years <n>",
            )
        )
    for variant in found.variants:
        step = NEXT_STEP.get(variant.state or "")
        if step is not None:
            found.waiting.append(
                Waiting(
                    variant.id,
                    f"{step} is judged next",
                    f"pkit lean judge {variant.id} {step} yes|no",
                )
            )
        elif variant.state == positions.FEASIBLE:
            found.waiting.append(
                Waiting(variant.id, "it may be shortlisted", f"pkit lean shortlist {variant.id}")
            )
    return found


def document(location: str, ideas: list[IdeaStatus]) -> dict[str, Any]:
    """The structured form."""
    return {
        "schema_version": SCHEMA_VERSION,
        "location": location,
        "ideas": [idea.as_data() for idea in ideas],
    }


def line(idea: IdeaStatus) -> str:
    """One line for the idea."""
    counted: dict[str, int] = {}
    for variant in idea.variants:
        key = variant.state or "unknown"
        counted[key] = counted.get(key, 0) + 1
    states = ", ".join(f"{count} {state}" for state, count in counted.items())
    variants = f"{len(idea.variants)} variant{'s' if len(idea.variants) != 1 else ''}"
    goal = "a goal" if idea.goal is not None else "no goal"
    waits = f"; {len(idea.waiting)} waiting" if idea.waiting else ""
    return f"{idea.id}: {goal}, {variants}{f' ({states})' if states else ''}{waits}"


def lines(idea: IdeaStatus) -> list[str]:
    """The idea's status, in full."""
    out = [f"The idea `{idea.id}`"]
    goal = _goal_data(idea.goal)
    if goal is None:
        out.append("  goal: none yet")
    else:
        out.append(
            f"  goal: {goal['revenue']} {goal['currency']} a {goal['per']}, within "
            f"{goal['years']} years"
        )
    for title, held in (
        ("variants", idea.variants),
        ("cycles", idea.cycles),
        ("experiments", idea.experiments),
    ):
        if not held:
            continue
        out.append(f"  {title}:")
        for subject in held:
            where = subject.state or f"cannot be told: {subject.why}"
            out.append(f"    {subject.id}: {where}")
    if idea.waiting:
        out.append("  waiting on you:")
        for waiting in idea.waiting:
            out.append(f"    {waiting.subject}: {waiting.what}")
            out.append(f"      {waiting.command}")
    else:
        out.append("  nothing waits on you at the desk")
    return out
