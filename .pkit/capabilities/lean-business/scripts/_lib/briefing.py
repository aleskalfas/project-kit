"""The status of the ideas, and the briefing that orients a person coming back to one: where
each idea and each of its subjects stands, and what waits on the person (lean-business
DEC-001 point 10; DEC-002 points 12 and 15).

It is worked out from the files each time it is shown and kept nowhere. Each subject's
position is the process engine's (`engine`), never worked out here again; where a window
or a time box falls is the one predicate the check shares (`timeline`). Without an idea,
the status gives one line for each idea; with one, the briefing, in this order:

- **An offer** (`offer`), after a silence (`SILENCE`): where nothing has been recorded on
  a running cycle, or one in review, for that many days of its window, the gap may be
  recorded as a suspension, from the day after the last work recorded on the cycle, or
  from the window's first day where that is later. It is offered only where such a
  suspension, resumed today, keeps the suspension's rules (`suspensions.of_cycle`), and it
  says where the window's end falls now and where it would fall. It is an offer, never an
  act: only the person knows whether the silence was time away.
- **The last act** (`last_act`): the day of the person's last recorded act on the idea,
  and each act recorded that day.
- **The goal, the cycles, the variants and the experiments,** each with where it stands.
  The cycle not yet decided comes in full: its window as its suspensions move it, the days
  of it gone by today, its objective, key results and constraint, and its suspensions. A
  decided one comes in a line. A variant's stale judgements are marked. An experiment not
  yet decided comes with its time box, its declared expectation, and the result beside it
  or that it waits for one.
- **What waits on the person,** each with the command that takes it, what others wait on
  first: a suspended cycle to resume; a goal to set; a due experiment's result, then its
  next action; a cycle in review to review; a draft in an open cycle to declare; at the
  desk, a stale verdict to judge again, the next step to judge, a feasible variant to
  shortlist and a stale shortlisting to take again; and, where the idea has a goal, a fresh
  shortlisted variant and no cycle undecided, and its last cycle did not pause, the next
  cycle to plan.

**Its structured form** (`document`) is a contract its readers depend on (ADR-097): the
capability's README lists its keys. It carries `schema_version`; a change that would break
a reader raises it, and an added key leaves it.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from _lib import acts, fingerprint, ids, positions, readings, timeline
from _lib import cycles as cycle_words
from _lib import engine as engines
from _lib import suspensions as rules
from _lib.engine import Engine, EngineFailed
from _lib.fingerprint import STEPS
from _lib.model import Cycle, IdeaModel
from _lib.reading import day
from _lib.timeline import Span, span_text

#: The version of the structured form.
SCHEMA_VERSION = 1

#: The days of a cycle's window with nothing recorded on it after which the briefing offers
#: to record the gap as a suspension (DEC-001 point 10).
SILENCE = 14

#: The step judged next in each state of the desk stage that judges one.
NEXT_STEP = {
    positions.SKETCHED: STEPS[0],
    positions.DESIRABLE: STEPS[1],
    positions.VIABLE: STEPS[2],
}

#: A variant's judgement besides its verdicts that may go stale.
SHORTLISTING = "shortlisting"

#: The cycle's states in which the briefing offers to record a silence as a suspension.
OFFERED_IN = (positions.RUNNING, positions.IN_REVIEW)

#: What each command that takes a waiting item is given, past the subject.
RECORD_RESULT = "[--measured <number>] [--spoiled] --evidence <text> --learned <text>"
DECIDE = "correct-course|double-down|stop"
REVIEW = (
    "--reached <number>... [--winning <variant>] --decision persevere|pivot|pause "
    "--reasons <text> [--evidence <experiment>]..."
)
PLAN = (
    "--variant <variant>... --start <day> [--days <n>] --objective <text> "
    "--key-result <variant>:<step>:<target>... --constraint-step <step> "
    "--constraint-evidence <text>"
)


def _iso(when: date | None) -> str | None:
    return when.isoformat() if when is not None else None


def _m(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _span(span: Span | None) -> dict[str, Any] | None:
    if span is None:
        return None
    return {"start": _iso(span.start), "end": _iso(span.end)}


# --- what the status holds ------------------------------------------------------------------


@dataclass(frozen=True)
class Standing:
    """Where a subject stands: its id, its state or None, and why where the engine could
    not tell."""

    id: str
    state: str | None
    why: str = ""

    def as_data(self) -> dict[str, Any]:
        return {"id": self.id, "state": self.state, "why": self.why or None}

    @property
    def where(self) -> str:
        return self.state or f"cannot be told: {self.why}"


@dataclass(frozen=True)
class Waiting:
    """Something that waits on the person: what it is, and the command that takes it."""

    subject: str
    what: str
    command: str

    def as_data(self) -> dict[str, Any]:
        return {"subject": self.subject, "what": self.what, "command": self.command}


@dataclass(frozen=True)
class LastAct:
    """The day of the person's last recorded act on an idea, and each act recorded that
    day, in words."""

    day: date
    what: tuple[str, ...]

    def as_data(self) -> dict[str, Any]:
        return {"day": self.day.isoformat(), "what": list(self.what)}


@dataclass(frozen=True)
class Offer:
    """The offer to record a silence on a cycle as a suspension: the cycle, the day of the
    last work recorded on it, the first day the suspension would cover, and where the
    window's end falls now and where it would fall were the person back today."""

    cycle: str
    last_work: date | None
    first_day: date
    end: date | None
    end_if_back: date | None

    @property
    def command(self) -> str:
        return (
            f"pkit lean suspend {self.cycle} --reason <why> --since {self.first_day} "
            f"--resumed <the day you came back>"
        )

    def as_data(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "last_work": _iso(self.last_work),
            "first_day": self.first_day.isoformat(),
            "window_end": _iso(self.end),
            "window_end_if_back_today": _iso(self.end_if_back),
            "command": self.command,
        }

    def lines(self) -> list[str]:
        since = f"since {self.last_work}" if self.last_work is not None else "since it was planned"
        ends = f", {self.end}," if self.end is not None else ""
        back = f": to {self.end_if_back}, were you back today" if self.end_if_back else ""
        return [
            f"Nothing has been recorded on `{self.cycle}` {since}. If you were away, the gap "
            f"can be recorded as a suspension from {self.first_day}, which would move the "
            f"window's end{ends} later by the days you were away{back}.",
            f"  {self.command}",
        ]


@dataclass(frozen=True)
class VariantStatus:
    """A variant's position, and each of its judgements gone stale."""

    at: Standing
    stale: tuple[str, ...] = ()

    def as_data(self) -> dict[str, Any]:
        return {**self.at.as_data(), "stale": list(self.stale)}


@dataclass(frozen=True)
class CycleStatus:
    """A cycle's position, and what its file says that the briefing shows: None where its
    file does not read."""

    at: Standing
    data: Mapping[str, Any] | None
    on: date

    @property
    def decided(self) -> bool:
        """Whether the cycle is decided: a cycle whose file does not read counts as not."""
        return self.data is not None and self.at.state == positions.DECIDED

    @property
    def window(self) -> Span | None:
        return timeline.cycle_window(self.data) if self.data is not None else None

    @property
    def days(self) -> int | None:
        held = _m(_m(self.data).get("window")).get("days")
        return held if isinstance(held, int) and not isinstance(held, bool) else None

    def counted(self) -> int | None:
        """The days of the window gone by `on`, its first day through `on` or its end, the
        days a suspension covers not counted."""
        window = self.window
        if window is None:
            return None
        if window.start is None or window.start > self.on:
            return 0
        last = self.on if window.end is None else min(self.on, window.end)
        covered = timeline.covered_by(_m(self.data).get("suspensions"))
        return sum(
            1
            for offset in range((last - window.start).days + 1)
            if not any(run.covers(window.start + timedelta(days=offset)) for run in covered)
        )

    def key_results(self) -> list[dict[str, Any]]:
        data = _m(self.data)
        reached = _list(_m(data.get("review")).get("reached"))
        found: list[dict[str, Any]] = []
        for index, result in enumerate(_list(_m(data.get("objective")).get("key-results"))):
            held = _m(result)
            named = ids.parse_ref(held.get("variant"), ids.CANVAS)
            found.append(
                {
                    "variant": named.id if named is not None else None,
                    "metric": _text(held.get("metric")),
                    "target": _number(held.get("target")),
                    "reached": _number(reached[index]) if index < len(reached) else None,
                }
            )
        return found

    def as_data(self) -> dict[str, Any]:
        """The cycle's keys, each null where its file does not read, its lists too, since
        an empty one would say the cycle holds none."""
        data = self.data
        window = self.window
        constraint = _m(data).get("constraint")
        review = _m(data).get("review")
        winning = ids.parse_ref(_m(review).get("winning"), ids.CANVAS)
        return {
            **self.at.as_data(),
            "window": (
                {**(_span(window) or {}), "days": self.days, "counted": self.counted()}
                if window is not None
                else None
            ),
            "objective": _text(_m(_m(data).get("objective")).get("statement")),
            "key_results": self.key_results() if data is not None else None,
            "constraint": (
                {
                    "step": _text(_m(constraint).get("step")),
                    "evidence": _text(_m(constraint).get("evidence")),
                }
                if isinstance(constraint, Mapping)
                else None
            ),
            "suspensions": (
                [
                    {
                        "reason": _text(entry.get("reason")),
                        "first_day": _iso(day(entry.get("first-day"))),
                        "resumed": _iso(day(_m(entry.get("resumed")).get("day"))),
                        "recorded": _iso(day(entry.get("when"))),
                    }
                    for entry in cycle_words.suspensions_of(data)
                ]
                if data is not None
                else None
            ),
            "review": (
                {
                    "decision": _text(_m(review).get("decision")),
                    "winning": winning.id if winning is not None else None,
                    "when": _iso(day(_m(review).get("when"))),
                }
                if isinstance(review, Mapping)
                else None
            ),
        }

    def lines(self) -> list[str]:
        data = self.data
        if data is None:
            return [f"    {self.at.id}: {self.at.where}"]
        window = self.window
        falls = span_text(window) if window is not None else "a window that does not read"
        if self.at.state == positions.DECIDED:
            review = _m(data.get("review"))
            winning = ids.parse_ref(review.get("winning"), ids.CANVAS)
            named = f" for `{winning.id}`" if winning is not None else ""
            return [f"    {self.at.id}: decided, {review.get('decision')}{named}; window {falls}"]
        counted, days = self.counted(), self.days
        # A window not yet started has no day of it gone to show.
        gone = f", day {counted} of {days}" if counted and days is not None else ""
        out = [f"    {self.at.id}: {self.at.where}{gone}; window {falls}"]
        objective = _text(_m(data.get("objective")).get("statement"))
        if objective is not None:
            out.append(f"      objective: {objective}")
        for result in self.key_results():
            reached = f", reached {result['reached']}" if result["reached"] is not None else ""
            out.append(
                f"      key result: `{result['variant']}`, {result['metric']}, target "
                f"{result['target']}{reached}"
            )
        constraint = _m(data.get("constraint"))
        if constraint:
            out.append(f"      constraint: {constraint.get('step')}: {constraint.get('evidence')}")
        for entry in cycle_words.suspensions_of(data):
            out.append(f"      suspended {cycle_words.away(entry)}")
        return out


@dataclass(frozen=True)
class ExperimentStatus:
    """An experiment's position, and what its file says that the briefing shows: None where
    its file does not read."""

    at: Standing
    data: Mapping[str, Any] | None
    cycle: Mapping[str, Any] | None

    @property
    def time_box(self) -> Span | None:
        if self.data is None:
            return None
        return timeline.experiment_time_box(self.data, self.cycle)

    def expected(self) -> str | None:
        """What it declared it expects, in words."""
        held = _m(self.data)
        if held.get("kind") == "generative":
            fit = _m(held.get("fit"))
            if fit.get("count") is None:
                return None
            return f"a fit of {fit.get('count')} {fit.get('of')}"
        expected = _m(held.get("expected"))
        direction = {"at-least": "at least", "at-most": "at most"}.get(
            str(expected.get("direction"))
        )
        if direction is None:
            return None
        metric = held.get("metric")
        threshold = _number(expected.get("threshold"))
        if threshold is not None:
            return f"{metric} {direction} {threshold}"
        span = _m(expected.get("range"))
        bound = span.get("low") if expected.get("direction") == "at-least" else span.get("high")
        return (
            f"{metric} {direction} {bound}, of a 90% range from {span.get('low')} to "
            f"{span.get('high')}"
        )

    def outcome(self) -> str | None:
        return readings.experiment_outcome(self.data) if self.data is not None else None

    def as_data(self) -> dict[str, Any]:
        cycle = ids.parse_ref(_m(self.data).get("cycle"), ids.CYCLE)
        return {
            **self.at.as_data(),
            "kind": _text(_m(self.data).get("kind")),
            "cycle": cycle.id if cycle is not None else None,
            "time_box": _span(self.time_box),
            "expected": self.expected(),
            "outcome": self.outcome(),
        }

    def lines(self) -> list[str]:
        data = self.data
        if data is None:
            return [f"    {self.at.id}: {self.at.where}"]
        outcome = self.outcome()
        decision = _m(data.get("decision"))
        if self.at.state == positions.DECIDED:
            next_action = positions.NEXT_ACTIONS.get(str(decision.get("next")), "decided")
            result = f"; its result, {positions.OUTCOME_WORDS[outcome]}" if outcome else ""
            return [f"    {self.at.id}: decided, {next_action}{result}"]
        box = self.time_box
        if self.at.state == positions.DRAFTED or box is None:
            days = ""
        elif box.start is None:
            days = "; its time box waits for its cycle to resume"
        else:
            days = f"; {span_text(box)}"
        out = [f"    {self.at.id}: {self.at.where}{days}"]
        if self.at.state == positions.DRAFTED:
            return out
        expected = self.expected()
        if expected is not None:
            out.append(f"      expected: {expected}")
        if outcome is None:
            out.append("      result: waits for its result")
        else:
            measured = _m(data.get("result")).get("measured")
            spoiled = _m(data.get("result")).get("spoiled") is True
            how = "spoiled" if spoiled else f"measured {measured}"
            out.append(f"      result: {positions.OUTCOME_WORDS[outcome]}, {how}")
        return out


@dataclass
class IdeaStatus:
    """An idea's status: its goal, each subject with where it stands, what waits, the last
    act and, after a silence, the offer to record it."""

    id: str
    goal: Mapping[str, Any] | None
    variants: list[VariantStatus] = field(default_factory=list)
    cycles: list[CycleStatus] = field(default_factory=list)
    experiments: list[ExperimentStatus] = field(default_factory=list)
    waiting: list[Waiting] = field(default_factory=list)
    last_act: LastAct | None = None
    offer: Offer | None = None

    def as_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": _goal_data(self.goal),
            "last_act": self.last_act.as_data() if self.last_act is not None else None,
            "offer": self.offer.as_data() if self.offer is not None else None,
            "variants": [v.as_data() for v in self.variants],
            "cycles": [c.as_data() for c in self.cycles],
            "experiments": [e.as_data() for e in self.experiments],
            "waiting": [w.as_data() for w in self.waiting],
        }


def _goal_data(goal: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if goal is None:
        return None
    revenue = _m(goal.get("revenue"))
    return {
        "revenue": revenue.get("amount"),
        "per": revenue.get("per"),
        "currency": goal.get("currency"),
        "years": goal.get("years"),
    }


# --- worked out from the files --------------------------------------------------------------


def _standing(engine: Engine, process: str, subject: str) -> Standing:
    try:
        found = engine.status(process, subject)
    except EngineFailed as exc:
        return Standing(subject, None, str(exc))
    if found.indeterminate:
        return Standing(subject, None, found.why or "the engine cannot tell")
    return Standing(subject, found.state)


def of_idea(engine: Engine, idea: IdeaModel, on: date) -> IdeaStatus:
    """The status of `idea` on the day `on`, each subject's position asked of `engine`.
    Each subject whose file lies in its place is listed, with its data where the file
    reads."""
    name = idea.name
    found = IdeaStatus(name, idea.goal)
    canvases = {own: data for own, _, data in idea.canvases()}
    for own in sorted(idea.idea.variants):
        at = _standing(engine, engines.DESK, ids.qualify(name, own))
        held = canvases.get(own)
        stale = _stale(held, idea) if held is not None else ()
        found.variants.append(VariantStatus(at, stale))
    for own, file in sorted(idea.idea.cycles.items()):
        at = _standing(engine, engines.CYCLE, idea.qualified(own))
        found.cycles.append(CycleStatus(at, file.data, on))
    by_id = {c.at.id: c.data for c in found.cycles if c.data is not None}
    for own, file in sorted(idea.idea.experiments.items()):
        at = _standing(engine, engines.EXPERIMENT, idea.qualified(own))
        named = ids.parse_ref(_m(file.data).get("cycle"), ids.CYCLE)
        cycle = by_id.get(named.id) if named is not None else None
        found.experiments.append(ExperimentStatus(at, file.data, cycle))
    found.last_act = last_act(idea)
    found.offer = offer(idea, found.cycles, on)
    found.waiting = list(_waiting(idea, found))
    return found


def _stale(canvas: Mapping[str, Any], idea: IdeaModel) -> tuple[str, ...]:
    """The judgements of a variant of `idea` gone stale, each verdict by its step and the
    shortlisting, none where its outcome is final. Where the idea's goal file does not
    read, whether a verdict judged against the goal, or the shortlisting, is stale cannot
    be told, so neither is marked, as the check marks neither."""
    outcome = _m(canvas.get("outcome"))
    if outcome.get("kind") in positions.FINAL:
        return ()
    unread = idea.goal_unread
    found = [
        step
        for step in STEPS
        if not (unread and step in positions.AGAINST_THE_GOAL)
        and readings.answer(canvas, step) is not None
        and fingerprint.check_verdict(step, canvas, idea.goal).stale
    ]
    if (
        not unread
        and outcome.get("kind") == "shortlisted"
        and fingerprint.check_shortlisting(canvas, idea.goal).stale
    ):
        found.append(SHORTLISTING)
    return tuple(found)


def _acts(idea: IdeaModel) -> Iterator[tuple[date, str]]:
    """Each act recorded on the idea, with its day, in words: the goal set; each variant's
    verdicts and outcome; each cycle's planning, the last change to its plan, its
    suspensions, their resumptions and its review; and each experiment's declaration,
    stopping rule reached, result and decision."""

    def at(value: object, what: str) -> Iterator[tuple[date, str]]:
        when = day(value)
        if when is not None:
            yield when, what

    if idea.goal is not None:
        yield from at(idea.goal.get("when"), "the goal set")
    for own, _, canvas in idea.canvases():
        variant = idea.qualified(own)
        for step in STEPS:
            verdict = _m(_m(canvas.get("verdicts")).get(step))
            yield from at(verdict.get("when"), f"the verdict on {step} of `{variant}`")
        outcome = _m(canvas.get("outcome"))
        yield from at(outcome.get("when"), f"`{variant}` {outcome.get('kind')}")
    for cycle in idea.cycles:
        named = idea.qualified(cycle.own)
        planned = _m(cycle.data.get("planned"))
        first = _m(planned.get("first")).get("when")
        yield from at(first, f"the planning of `{named}`")
        if planned.get("when") != first:
            yield from at(planned.get("when"), f"a change to the plan of `{named}`")
        for entry in cycle_words.suspensions_of(cycle.data):
            yield from at(entry.get("when"), f"a suspension of `{named}`")
            yield from at(_m(entry.get("resumed")).get("when"), f"the resumption of `{named}`")
        yield from at(_m(cycle.data.get("review")).get("when"), f"the review of `{named}`")
    for experiment in idea.experiments:
        named = idea.qualified(experiment.own)
        for key, what in (
            ("declared", "the declaration"),
            ("stopped", "the stopping rule reached"),
            ("result", "the result"),
            ("decision", "the decision"),
        ):
            yield from at(_m(experiment.data.get(key)).get("when"), f"{what} of `{named}`")


def last_act(idea: IdeaModel) -> LastAct | None:
    """The day of the last act recorded on `idea`, and each act recorded that day, or None
    where none is recorded."""
    found = list(_acts(idea))
    if not found:
        return None
    last = max(when for when, _ in found)
    return LastAct(last, tuple(what for when, what in found if when == last))


def offer(idea: IdeaModel, statuses: Sequence[CycleStatus], on: date) -> Offer | None:
    """The offer to record a silence of `SILENCE` days or more on a cycle running or in
    review as a suspension, or None where no cycle has one, or where such a suspension,
    resumed on `on`, would break the suspension's rules. A cycle whose file does not read
    has none: it counts as undecided, and where it stands cannot be told."""
    for status in statuses:
        if status.data is None or status.at.state not in OFFERED_IN:
            continue
        cycle = next((c for c in idea.cycles if idea.qualified(c.own) == status.at.id), None)
        window = status.window
        if cycle is None or window is None or window.start is None:
            continue
        bearing = acts.bearing_on(idea, cycle)
        last = _last_work(cycle, bearing)
        # The silence runs from the last day with work recorded, or from the window's first
        # day where nothing was recorded since it began.
        quiet = window.start - timedelta(days=1)
        if last is not None and last > quiet:
            quiet = last
        if (on - quiet).days < SILENCE:
            continue
        first = quiet + timedelta(days=1)
        candidate = _suspended(cycle.data, first, on)
        index = len(_list(candidate.get("suspensions"))) - 1
        if any(found.index == index for found in rules.of_cycle(candidate, bearing)):
            continue
        after = timeline.cycle_window(candidate)
        return Offer(
            status.at.id, last, first, window.end, after.end if after is not None else None
        )
    return None


def _last_work(cycle: Cycle, bearing: Sequence[acts.Act]) -> date | None:
    """The last day work was recorded on `cycle`: an act its suspensions bear on, a
    suspension recorded, or a day it resumed or its resumption was recorded."""
    days = [act.day for act in bearing]
    for entry in cycle_words.suspensions_of(cycle.data):
        resumed = _m(entry.get("resumed"))
        for value in (entry.get("when"), resumed.get("day"), resumed.get("when")):
            when = day(value)
            if when is not None:
                days.append(when)
    return max(days) if days else None


def _suspended(cycle: Mapping[str, Any], first: date, on: date) -> dict[str, Any]:
    """`cycle` with a suspension from `first`, recorded and resumed on `on`, as the offer
    would record it."""
    entry = {
        "reason": "away",
        "first-day": first.isoformat(),
        "when": on.isoformat(),
        "resumed": {"day": on.isoformat(), "when": on.isoformat()},
    }
    return {**cycle, "suspensions": [*_list(cycle.get("suspensions")), entry]}


# --- what waits on the person ---------------------------------------------------------------


def _waiting(idea: IdeaModel, status: IdeaStatus) -> Iterator[Waiting]:
    """What waits on the person, in the order the briefing gives it."""
    name = idea.name
    for cycle in status.cycles:
        if cycle.at.state == positions.SUSPENDED:
            yield Waiting(
                cycle.at.id,
                "it is suspended, and nothing is recorded on it until it resumes, on the day "
                "you came back",
                f"pkit lean resume {cycle.at.id} [--on <day>]",
            )
    if idea.goal is None and not idea.goal_unread:
        yield Waiting(
            name,
            "the idea has no goal, which viability and feasibility are judged against",
            f"pkit lean set-goal {name} --revenue <amount> --per month|year "
            f"--currency <code> --years <n>",
        )
    for experiment in status.experiments:
        if experiment.at.state != positions.DUE:
            continue
        subject = experiment.at.id
        if experiment.outcome() is None:
            yield Waiting(
                subject,
                "its time box ended, and its result waits",
                f"pkit lean record-result {subject} {RECORD_RESULT}",
            )
        else:
            yield Waiting(
                subject,
                "its result is recorded, and your next action waits",
                f"pkit lean decide {subject} {DECIDE}",
            )
    for cycle in status.cycles:
        if cycle.at.state == positions.IN_REVIEW:
            yield Waiting(
                cycle.at.id,
                "its window ended, and its review waits",
                f"pkit lean review-cycle {cycle.at.id} {REVIEW}",
            )
    states = {cycle.at.id: cycle.at.state for cycle in status.cycles}
    for experiment in status.experiments:
        named = ids.parse_ref(_m(experiment.data).get("cycle"), ids.CYCLE)
        if (
            experiment.at.state == positions.DRAFTED
            and named is not None
            and states.get(named.id) in positions.OPEN
        ):
            yield Waiting(
                experiment.at.id,
                "a draft, which waits to be declared",
                f"pkit lean declare {experiment.at.id}",
            )
    yield from _desk(status.variants)
    planning = _planning(idea, status)
    if planning is not None:
        yield planning


def _desk(variants: Sequence[VariantStatus]) -> Iterator[Waiting]:
    """What waits at the desk, for each variant: a stale verdict to judge again, the next
    step to judge, a feasible variant to shortlist, and a stale shortlisting to take
    again."""
    for variant in variants:
        subject = variant.at.id
        for step in variant.stale:
            if step in STEPS:
                yield Waiting(
                    subject,
                    f"its verdict on {step} is stale: what it judged changed since",
                    f"pkit lean judge {subject} {step} yes|no",
                )
        step = NEXT_STEP.get(variant.at.state or "")
        # A step whose verdict is stale is judged again, listed above, by the same command.
        if step is not None and step not in variant.stale:
            yield Waiting(
                subject, f"{step} is judged next", f"pkit lean judge {subject} {step} yes|no"
            )
        elif variant.at.state == positions.FEASIBLE:
            yield Waiting(subject, "it may be shortlisted", f"pkit lean shortlist {subject}")
        if SHORTLISTING in variant.stale:
            yield Waiting(
                subject,
                "its shortlisting is stale: once its verdicts stand, shortlist it again",
                f"pkit lean shortlist {subject}",
            )


def _planning(idea: IdeaModel, status: IdeaStatus) -> Waiting | None:
    """The next cycle to plan, where the idea has a goal and a shortlisted variant whose
    shortlisting is not stale, no cycle of it is undecided, a cycle whose file does not
    read counted as undecided, and its last cycle did not pause; else None."""
    if idea.goal is None or not all(c.decided for c in status.cycles):
        return None
    reviewed = sorted(
        (
            (when, _m(_m(c.data).get("review")).get("decision"))
            for c in status.cycles
            if (when := day(_m(_m(c.data).get("review")).get("when"))) is not None
        ),
        key=lambda pair: pair[0],
    )
    if reviewed and reviewed[-1][1] == "pause":
        return None
    ready = [
        v.at.id
        for v in status.variants
        if v.at.state == positions.SHORTLISTED and SHORTLISTING not in v.stale
    ]
    if not ready:
        return None
    return Waiting(
        idea.name,
        f"no cycle is open, and {', '.join(f'`{v}`' for v in ready)} "
        f"{'is' if len(ready) == 1 else 'are'} shortlisted: the next cycle waits to be planned",
        f"pkit lean plan-cycle {idea.name}--<cycle> {PLAN}",
    )


# --- shown ----------------------------------------------------------------------------------


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
        key = variant.at.state or "unknown"
        counted[key] = counted.get(key, 0) + 1
    states = ", ".join(f"{count} {state}" for state, count in counted.items())
    variants = f"{len(idea.variants)} variant{'s' if len(idea.variants) != 1 else ''}"
    goal = "a goal" if idea.goal is not None else "no goal"
    waits = f"; {len(idea.waiting)} waiting" if idea.waiting else ""
    return f"{idea.id}: {goal}, {variants}{f' ({states})' if states else ''}{waits}"


def lines(idea: IdeaStatus) -> list[str]:
    """The idea's briefing, in full."""
    out = [f"The idea `{idea.id}`"]
    if idea.offer is not None:
        out.extend(f"  {each}" for each in idea.offer.lines())
    if idea.last_act is not None:
        out.append(f"  last act: on {idea.last_act.day}, {', '.join(idea.last_act.what)}")
    goal = _goal_data(idea.goal)
    if goal is None:
        out.append("  goal: none yet")
    else:
        out.append(
            f"  goal: {goal['revenue']} {goal['currency']} a {goal['per']}, within "
            f"{goal['years']} years"
        )
    if idea.cycles:
        out.append("  cycles:")
        for cycle in idea.cycles:
            out.extend(cycle.lines())
    if idea.variants:
        out.append("  variants:")
        for variant in idea.variants:
            stale = f"; stale: {', '.join(variant.stale)}" if variant.stale else ""
            out.append(f"    {variant.at.id}: {variant.at.where}{stale}")
    if idea.experiments:
        out.append("  experiments:")
        for experiment in idea.experiments:
            out.extend(experiment.lines())
    if idea.waiting:
        out.append("  waiting on you:")
        for waiting in idea.waiting:
            out.append(f"    {waiting.subject}: {waiting.what}")
            out.append(f"      {waiting.command}")
    else:
        out.append("  nothing waits on you")
    return out
