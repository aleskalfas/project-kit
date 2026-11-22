"""The status of the ideas, and the briefing that orients a person coming back to one: where
each idea and each of its subjects stands, and what waits on the person (lean-business
DEC-001 point 10; DEC-002 points 12 and 15).

It is worked out from the files each time it is shown and kept nowhere. Each subject's
position is the process engine's (`engine`), never worked out here again; where a window
or a time box falls is the one predicate the check shares (`timeline`). Without an idea,
the status gives one line for each idea; with one, the briefing, in this order:

- **Its first line** names the idea, and says where the idea is dropped, or where whether
  it is cannot be told (`readings.dropped`, which `shelve` reads too; DEC-003 point 8).
- **An offer** (`offer`), after a silence (`SILENCE`): where nothing has been recorded on
  a running cycle, or one in review, for that many days of its window, the gap may be
  recorded as a suspension, from the day after the last work recorded on the cycle, or
  from the window's first day where that is later. Only the silent days within the window
  count: those after the last work, through today or through the window's end where that
  is earlier, so a cycle long in review is not offered the days after its window. It is
  offered only where such a suspension, resumed today, keeps the suspension's rules
  (`suspensions.of_cycle`), and it says where the window's end falls now and where it
  would fall. It is an offer, never an act: only the person knows whether the silence was
  time away.
- **The last act** (`last_act`): the day of the person's last recorded act on the idea,
  and each act recorded that day.
- **The goal, the cycles and the variants,** each with where it stands. The cycle not yet
  decided comes in full: its window as its suspensions move it, the days of it gone by
  today, its objective, key results and constraint, and its suspensions. A decided one
  comes in a line. A variant's stale judgements are marked, and its assumptions come the
  riskiest first, each with its outcome, worked out here and stored nowhere from the
  experiments that test it (`readings.assumption_outcome`, which the declaring command's
  warning reads too; DEC-003 point 8).
- **The canvases** of the variants in play, each variant neither shelved nor split whose
  canvas reads, drawn as `pkit lean canvas` draws one (`grid`), its credit line beneath,
  in the plain form only (DEC-002 point 15; DEC-001 point 6).
- **The experiments,** each with where it stands. One declared and not yet decided comes
  with its time box, its declared expectation, and the result beside it or that it waits
  for one.
- **What waits on the person,** each with the command that takes it, what others wait on
  first: a suspended cycle to resume; a goal to set; a due experiment's result, then its
  next action; a cycle in review to review; a draft in an open cycle to declare; at the
  desk, a stale verdict to judge again, the next step to judge, a feasible variant to
  shortlist and a stale shortlisting to take again; and, where the idea has a goal, a fresh
  shortlisted variant and no cycle undecided, and its last cycle did not pause, the next
  cycle to plan.

**The plain form** reads each value the structured form gives too as that form reads it,
and says in its place where one does not read, rather than print what the file holds.

**Its structured form** (`document`) is a contract its readers depend on (ADR-097): the
capability's README lists its keys, and the values of each set. A value a file holds
outside its set does not read, so the form gives it as null (`_among`). It carries
`schema_version`; a change that would break a reader raises it, and an added key leaves
it.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from _lib import acts, estimates, fingerprint, grid, ids, model, positions, readings, timeline
from _lib import canvases as canvas_words
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
#: to record the gap as a suspension. DEC-001 point 10 leaves how long a silence must be to
#: the build, which sets it at three weeks; use may show it should change.
SILENCE = 21

#: The step judged next in each state of the desk stage that judges one.
NEXT_STEP = {
    positions.SKETCHED: STEPS[0],
    positions.DESIRABLE: STEPS[1],
    positions.VIABLE: STEPS[2],
}

#: A variant's judgement besides its verdicts that may go stale.
SHORTLISTING = "shortlisting"

#: Each value of the goal, in words, by its key in the structured form.
GOAL_WORDS = {"revenue": "revenue", "per": "period", "currency": "currency", "years": "years"}

#: Each outcome of an assumption, in words (DEC-003 point 8).
ASSUMPTION_WORDS = {
    readings.UNTESTED: "untested",
    readings.BEING_TESTED: "being tested",
    readings.SUPPORTED: "supported",
    readings.REFUTED: "refuted",
    readings.INCONCLUSIVE: "inconclusive",
}

#: The cycle's states in which the briefing offers to record a silence as a suspension.
OFFERED_IN = (positions.RUNNING, positions.IN_REVIEW)

#: What the plain form says of a step of the customer factory that does not read, where the
#: structured form gives null.
UNREAD_STEP = "a step that cannot be read"

#: The directions of an evaluative experiment's expectation, each in words.
DIRECTIONS = {"at-least": "at least", "at-most": "at most"}

#: The part of an experiment's file that holds its expectation, by its kind.
EXPECTATION_KEY = {"generative": "fit", "evaluative": "expected"}

#: What each command that takes a waiting item is given, past the subject.
RECORD_RESULT = "[--measured <number>] [--spoiled] --evidence <text> --learned <text>"
DECIDE = "correct-course|double-down|stop"
REVIEW = (
    "--reached <number> [--reached <number>]... [--winning <variant>] "
    "--decision persevere|pivot|pause --reasons <text> [--evidence <experiment>]..."
)
PLAN = (
    "--variant <variant> [--variant <variant>]... --start <day> [--days <n>] "
    "--objective <text> --key-result <variant>:<step>:<target> "
    "[--key-result <variant>:<step>:<target>]... --constraint-step <step> "
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


def _among(value: object, values: Sequence[str]) -> str | None:
    """`value` where it is one of the set `values`, else None: a value outside its set does
    not read as one of it."""
    return value if isinstance(value, str) and value in values else None


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
class AssumptionStatus:
    """An assumption of a variant: its id and its rank, each None where it does not read,
    and its outcome, None where it cannot be told."""

    id: str | None
    rank: int | None
    outcome: str | None

    def as_data(self) -> dict[str, Any]:
        return {"id": self.id, "rank": self.rank, "outcome": self.outcome}

    def line(self) -> str:
        rank = f" {self.rank}" if self.rank is not None else ", its rank unread,"
        named = f"`{self.id}`" if self.id is not None else "whose id cannot be read"
        outcome = ASSUMPTION_WORDS.get(self.outcome or "", "its outcome cannot be told")
        return f"      assumption{rank} {named}: {outcome}"


@dataclass(frozen=True)
class VariantStatus:
    """A variant's position, each of its judgements gone stale, its canvas, None where its
    file does not read, and its assumptions, the riskiest first, or the file that holds
    them where it, or the list it holds, does not read."""

    at: Standing
    stale: tuple[str, ...] = ()
    canvas: Mapping[str, Any] | None = None
    assumptions: tuple[AssumptionStatus, ...] = ()
    assumptions_unread: str | None = None

    @property
    def in_play(self) -> bool:
        """Whether the variant is in play: neither shelved nor split. One whose position
        cannot be told counts as in play, since it may be."""
        return self.at.state not in positions.FINAL

    def as_data(self) -> dict[str, Any]:
        return {
            **self.at.as_data(),
            "stale": list(self.stale),
            "assumptions": (
                [a.as_data() for a in self.assumptions] if self.assumptions_unread is None else None
            ),
        }

    def lines(self) -> list[str]:
        stale = f"; stale: {', '.join(self.stale)}" if self.stale else ""
        out = [f"    {self.at.id}: {self.at.where}{stale}"]
        if self.assumptions_unread is not None:
            out.append(f"      its assumptions, in `{self.assumptions_unread}`, cannot be read")
        out.extend(assumption.line() for assumption in self.assumptions)
        return out


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

    def key_results(self) -> list[dict[str, Any]] | None:
        """The key results of the cycle's objective, each value None where it does not read,
        an entry that does not read listed all the same; None where the list does not read,
        since an empty one would say the cycle holds none."""
        data = _m(self.data)
        listed = _m(data.get("objective")).get("key-results")
        if not isinstance(listed, list):
            return None
        reached = _list(_m(data.get("review")).get("reached"))
        found: list[dict[str, Any]] = []
        for index, result in enumerate(listed):
            held = _m(result)
            named = ids.parse_ref(held.get("variant"), ids.CANVAS)
            found.append(
                {
                    "variant": named.id if named is not None else None,
                    "metric": _among(held.get("metric"), canvas_words.FACTORY_STEPS),
                    "target": _number(held.get("target")),
                    "reached": _number(reached[index]) if index < len(reached) else None,
                }
            )
        return found

    def constraint(self) -> dict[str, Any] | None:
        """The cycle's constraint, its step and its evidence, each None where it does not
        read; None where the constraint does not read, as where the file gives none, since
        every cycle holds one."""
        held = _m(self.data).get("constraint")
        if not isinstance(held, Mapping):
            return None
        return {
            "step": _among(held.get("step"), canvas_words.FACTORY_STEPS),
            "evidence": _text(held.get("evidence")),
        }

    def suspensions(self) -> list[object] | None:
        """The suspensions the cycle's file lists, each as the file holds it: empty where the
        file gives no list, as a cycle never suspended does not, and None where the list
        does not read, or the file does not."""
        if self.data is None:
            return None
        listed = self.data.get("suspensions", [])
        return listed if isinstance(listed, list) else None

    def as_data(self) -> dict[str, Any]:
        """The cycle's keys, each null where its file does not read. A list is null too
        where it does not read itself, since an empty one would say the cycle holds none."""
        data = self.data
        window = self.window
        review = _m(data).get("review")
        winning = ids.parse_ref(_m(review).get("winning"), ids.CANVAS)
        suspensions = self.suspensions()
        return {
            **self.at.as_data(),
            "window": (
                {**(_span(window) or {}), "days": self.days, "counted": self.counted()}
                if window is not None
                else None
            ),
            "objective": _text(_m(_m(data).get("objective")).get("statement")),
            "key_results": self.key_results(),
            "constraint": self.constraint(),
            "suspensions": (
                [_suspension(entry) for entry in suspensions] if suspensions is not None else None
            ),
            "review": (
                {
                    "decision": _among(_m(review).get("decision"), positions.DECISIONS),
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
            decision = _among(review.get("decision"), positions.DECISIONS)
            winning = ids.parse_ref(review.get("winning"), ids.CANVAS)
            decided = decision or "a decision that cannot be read"
            named = f"`{winning.id}`" if winning is not None else "a variant that cannot be read"
            return [f"    {self.at.id}: decided, {decided} for {named}; window {falls}"]
        counted, days = self.counted(), self.days
        # A window not yet started has no day of it gone to show.
        gone = f", day {counted} of {days}" if counted and days is not None else ""
        out = [f"    {self.at.id}: {self.at.where}{gone}; window {falls}"]
        objective = _text(_m(data.get("objective")).get("statement"))
        out.append(
            f"      objective: {objective}"
            if objective is not None
            else "      its objective cannot be read"
        )
        results = self.key_results()
        if results is None:
            out.append("      its key results cannot be read")
        out.extend(f"      key result: {_key_result(result)}" for result in results or ())
        constraint = self.constraint()
        if constraint is None:
            out.append("      its constraint cannot be read")
        else:
            evidence = constraint["evidence"]
            out.append(
                f"      constraint: {constraint['step'] or UNREAD_STEP}: "
                f"{evidence if evidence is not None else 'evidence that cannot be read'}"
            )
        suspensions = self.suspensions()
        if suspensions is None:
            out.append("      its suspensions cannot be read")
        for entry in suspensions or ():
            out.append(
                f"      suspended {cycle_words.away(entry)}"
                if isinstance(entry, Mapping)
                else "      a suspension that cannot be read"
            )
        return out


def _suspension(entry: object) -> dict[str, Any]:
    """A suspension of a cycle's list as the structured form gives it, each value None where
    it does not read, all of them where the entry does not."""
    held = _m(entry)
    return {
        "reason": _text(held.get("reason")),
        "first_day": _iso(day(held.get("first-day"))),
        "resumed": _iso(day(_m(held.get("resumed")).get("day"))),
        "recorded": _iso(day(held.get("when"))),
    }


def _key_result(result: Mapping[str, Any]) -> str:
    """A key result of the structured form in words, each value it gives as null said not to
    read."""
    variant, target, reached = result["variant"], result["target"], result["reached"]
    named = f"`{variant}`" if variant is not None else "a variant that cannot be read"
    aimed = f"target {target}" if target is not None else "a target that cannot be read"
    gone = f", reached {reached}" if reached is not None else ""
    return f"{named}, {result['metric'] or UNREAD_STEP}, {aimed}{gone}"


@dataclass(frozen=True)
class Expectation:
    """What an experiment declared it expects: in words where each of its values reads, else
    None, with the values that do not, each named as the plain form says it."""

    words: str | None
    unread: tuple[str, ...] = ()

    @classmethod
    def of(cls, words: str | None, *values: tuple[str, object]) -> Expectation:
        """`words` where none of `values`, each a name and what it reads as, is None; else
        the expectation that names each that is."""
        unread = tuple(name for name, value in values if value is None)
        return cls(None, unread) if unread else cls(words)

    @property
    def said(self) -> str:
        """In words, or which of its values cannot be read."""
        if self.words is not None:
            return self.words
        return f"{positions.joined(self.unread)} cannot be read"


def _fit(fit: object) -> Expectation:
    """A generative experiment's fit: the count its result is held against, and what it
    counts."""
    held = _m(fit)
    count, counts = _number(held.get("count")), _text(held.get("of"))
    return Expectation.of(
        f"a fit of {count} {counts}", ("its fit's count", count), ("what its fit counts", counts)
    )


def _evaluated(metric: object, expected: object) -> Expectation:
    """An evaluative experiment's expectation: its metric, its direction, and the threshold
    its result is held against, or the 90% range whose bound in that direction it is held
    against. A threshold that does not read gives way to a range, as the result's reading
    does (`readings.experiment_outcome`)."""
    held = _m(expected)
    step = _among(metric, canvas_words.FACTORY_STEPS)
    direction = _among(held.get("direction"), tuple(DIRECTIONS))
    named = (("its metric", step), ("its direction", direction))
    going = f"{step} {DIRECTIONS.get(direction or '')}"
    threshold = _number(held.get("threshold"))
    if threshold is not None or "range" not in held:
        bound = "its threshold" if "threshold" in held else "its threshold or range"
        return Expectation.of(f"{going} {threshold}", *named, (bound, threshold))
    span = _m(held.get("range"))
    low, high = _number(span.get("low")), _number(span.get("high"))
    reached = low if direction == "at-least" else high
    return Expectation.of(
        f"{going} {reached}, of a 90% range from {low} to {high}",
        *named,
        ("its range's low", low),
        ("its range's high", high),
    )


def _measured(experiment: Mapping[str, Any]) -> str:
    """What an experiment's recorded result measured, in words: that a suspension spoiled it,
    that nothing was measured where it gives no measurement, or what it measured. A
    measurement that is not a number is no number to compare, so the result works out to
    neither, as where nothing was measured (`readings.experiment_outcome`), and it is said
    not to read."""
    result = _m(experiment.get("result"))
    if result.get("spoiled") is True:
        return "spoiled"
    if "measured" not in result:
        return "nothing measured"
    measured = _number(result.get("measured"))
    return f"measured {measured}" if measured is not None else "a measurement that cannot be read"


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

    def expectation(self) -> Expectation | None:
        """What it declared it expects, or None where its file gives no expectation and it
        is not declared, as a draft may give none. A declared experiment holds one, so one
        it does not give does not read."""
        held = _m(self.data)
        kind = _among(held.get("kind"), positions.KINDS)
        keys = (EXPECTATION_KEY[kind],) if kind is not None else tuple(EXPECTATION_KEY.values())
        if not any(key in held for key in keys) and not model.declared(held):
            return None
        if kind == "generative":
            return _fit(held.get("fit"))
        if kind == "evaluative":
            return _evaluated(held.get("metric"), held.get("expected"))
        return Expectation(None, ("its kind",))

    def expected(self) -> str | None:
        """What it declared it expects, in words, where each value of it reads; else None,
        as a value that does not read is."""
        expectation = self.expectation()
        return expectation.words if expectation is not None else None

    def outcome(self) -> str | None:
        return readings.experiment_outcome(self.data) if self.data is not None else None

    @property
    def result_unread(self) -> bool:
        """Whether its file holds a result that does not read as one. The outcome, the engine
        and the commands read such a result as none recorded, so its outcome is None, and the
        plain form says it cannot be read rather than that it waits for one."""
        held = _m(self.data)
        return "result" in held and not isinstance(held["result"], Mapping)

    def as_data(self) -> dict[str, Any]:
        cycle = ids.parse_ref(_m(self.data).get("cycle"), ids.CYCLE)
        assumption = ids.parse_ref(_m(self.data).get("assumption"), ids.ASSUMPTIONS)
        return {
            **self.at.as_data(),
            "kind": _among(_m(self.data).get("kind"), positions.KINDS),
            "assumption": assumption.id if assumption is not None else None,
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
            following = _among(decision.get("next"), tuple(positions.NEXT_ACTIONS))
            next_action = (
                positions.NEXT_ACTIONS[following]
                if following is not None
                else "its next action cannot be read"
            )
            if outcome is not None:
                result = f"; its result, {positions.OUTCOME_WORDS[outcome]}"
            else:
                result = "; its result cannot be read" if self.result_unread else ""
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
        expectation = self.expectation()
        if expectation is not None:
            out.append(f"      expected: {expectation.said}")
        if self.result_unread:
            out.append("      its result cannot be read")
        elif outcome is None:
            out.append("      result: waits for its result")
        else:
            out.append(f"      result: {positions.OUTCOME_WORDS[outcome]}, {_measured(data)}")
        return out


@dataclass
class IdeaStatus:
    """An idea's status: its goal, or the goal's file where it lies in its place but does
    not read, each subject with where it stands, what waits, the last act, after a silence
    the offer to record it, and whether the idea is dropped, None where that cannot be
    told."""

    id: str
    goal: Mapping[str, Any] | None
    goal_unread: str | None = None
    variants: list[VariantStatus] = field(default_factory=list)
    cycles: list[CycleStatus] = field(default_factory=list)
    experiments: list[ExperimentStatus] = field(default_factory=list)
    waiting: list[Waiting] = field(default_factory=list)
    last_act: LastAct | None = None
    offer: Offer | None = None
    dropped: bool | None = False

    def as_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": _goal_data(self.goal),
            "goal_why": self.goal_why,
            "dropped": self.dropped,
            "last_act": self.last_act.as_data() if self.last_act is not None else None,
            "offer": self.offer.as_data() if self.offer is not None else None,
            "variants": [v.as_data() for v in self.variants],
            "cycles": [c.as_data() for c in self.cycles],
            "experiments": [e.as_data() for e in self.experiments],
            "waiting": [w.as_data() for w in self.waiting],
        }

    @property
    def goal_why(self) -> str | None:
        """Why whether the idea has a goal cannot be told, where its file does not read."""
        if self.goal_unread is None:
            return None
        return f"the idea's goal at `{self.goal_unread}` cannot be read"


def _goal_data(goal: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """The goal's values, each None where it does not read as the value it is."""
    if goal is None:
        return None
    revenue = _m(goal.get("revenue"))
    return {
        "revenue": _number(revenue.get("amount")),
        "per": _among(revenue.get("per"), estimates.PERIODS),
        "currency": _text(goal.get("currency")),
        "years": _number(goal.get("years")),
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
    goal_unread = idea.idea.goal.rel if idea.goal_unread and idea.idea.goal is not None else None
    found = IdeaStatus(name, idea.goal, goal_unread)
    canvases = {own: data for own, _, data in idea.canvases()}
    told = all(file.data is not None for file in idea.idea.experiments.values())
    tested = [experiment.data for experiment in idea.experiments]
    for own, variant in sorted(idea.idea.variants.items()):
        at = _standing(engine, engines.DESK, ids.qualify(name, own))
        held = canvases.get(own)
        stale = _stale(held, idea) if held is not None else ()
        listed = variant.assumptions
        assumptions = _assumptions(listed.data, tested, told) if listed is not None else ()
        assumptions_unread = listed.rel if listed is not None and assumptions is None else None
        found.variants.append(VariantStatus(at, stale, held, assumptions or (), assumptions_unread))
    found.dropped = _dropped(idea)
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


def _assumptions(
    listed: Mapping[str, Any] | None, tested: Sequence[Mapping[str, Any]], told: bool
) -> tuple[AssumptionStatus, ...] | None:
    """The assumptions a variant's file `listed` holds, the riskiest first, those whose rank
    does not read last, each with its outcome worked out from `tested`, the files of its
    idea's experiments that read; None where the file, or the list it holds, does not read.
    An entry that does not read is listed all the same, each of its values None, so the list
    does not look whole without it. `told` is whether every experiment's file reads. Where
    one does not, it may test any assumption, so an outcome is told only where it is being
    tested, which no other experiment can change, and is otherwise None."""
    held = _m(listed).get("assumptions")
    if not isinstance(held, list):
        return None
    found: list[AssumptionStatus] = []
    for entry in held:
        if not isinstance(entry, Mapping):
            found.append(AssumptionStatus(None, None, None))
            continue
        named = _text(entry.get("id"))
        rank = entry.get("rank")
        ranked = rank if isinstance(rank, int) and not isinstance(rank, bool) else None
        outcome = readings.assumption_outcome(named, tested) if named is not None else None
        if not told and outcome != readings.BEING_TESTED:
            outcome = None
        found.append(AssumptionStatus(named, ranked, outcome))
    return tuple(sorted(found, key=lambda each: (each.rank is None, each.rank or 0)))


def _dropped(idea: IdeaModel) -> bool | None:
    """Whether `idea` is dropped, from its variants' canvases (`readings.dropped`). Where a
    canvas does not read, the idea is not dropped where a canvas that reads is neither
    shelved nor split, since that variant is in play; where each canvas that reads is
    shelved or split, whether it is dropped cannot be told, so None."""
    read = [
        variant.canvas.data if variant.canvas is not None else None
        for variant in idea.idea.variants.values()
    ]
    known = [data for data in read if data is not None]
    if len(known) == len(read):
        return readings.dropped(known)
    return False if known and not readings.dropped(known) else None


def _acts(idea: IdeaModel) -> Iterator[tuple[date, str]]:
    """Each act recorded on the idea, with its day, in words: those the check judges
    (`acts.recorded`), the goal set, each cycle's and each experiment's; and besides them
    each variant's verdicts and outcome, and each cycle's suspensions and their
    resumptions, which no gate judges as acts."""

    def at(value: object, what: str) -> Iterator[tuple[date, str]]:
        when = day(value)
        if when is not None:
            yield when, what

    yield from ((act.day, act.what) for act in acts.recorded(idea))
    for own, _, canvas in idea.canvases():
        variant = idea.qualified(own)
        for step in STEPS:
            verdict = _m(_m(canvas.get("verdicts")).get(step))
            yield from at(verdict.get("when"), f"the verdict on {step} of `{variant}`")
        outcome = _m(canvas.get("outcome"))
        kind = _among(outcome.get("kind"), tuple(positions.BY_OUTCOME))
        given = (
            f"`{variant}` {kind}"
            if kind is not None
            else f"an outcome of `{variant}` whose kind cannot be read"
        )
        yield from at(outcome.get("when"), given)
    for cycle in idea.cycles:
        named = idea.qualified(cycle.own)
        for entry in cycle_words.suspensions_of(cycle.data):
            yield from at(entry.get("when"), f"a suspension of `{named}`")
            yield from at(_m(entry.get("resumed")).get("when"), f"the resumption of `{named}`")


def last_act(idea: IdeaModel) -> LastAct | None:
    """The day of the last act recorded on `idea`, and each act recorded that day, or None
    where none is recorded."""
    found = list(_acts(idea))
    if not found:
        return None
    last = max(when for when, _ in found)
    return LastAct(last, tuple(what for when, what in found if when == last))


def offer(idea: IdeaModel, statuses: Sequence[CycleStatus], on: date) -> Offer | None:
    """The offer to record a silence of `SILENCE` days or more of its window on a cycle
    running or in review as a suspension, or None where no cycle has one, or where such a
    suspension, resumed on `on`, would break the suspension's rules. The silent days are
    those after the last work, through `on` or the window's end where that is earlier. A
    cycle whose file does not read has none: it counts as undecided, and where it stands
    cannot be told."""
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
        through = on if window.end is None else min(on, window.end)
        if (through - quiet).days < SILENCE:
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
    if idea.goal_unread is not None:
        goal = "a goal whose file cannot be read"
    else:
        goal = "a goal" if idea.goal is not None else "no goal"
    if idea.dropped is None:
        dropped = ", whether it is dropped cannot be told"
    else:
        dropped = ", dropped" if idea.dropped else ""
    waits = f"; {len(idea.waiting)} waiting" if idea.waiting else ""
    return f"{idea.id}: {goal}, {variants}{f' ({states})' if states else ''}{dropped}{waits}"


def lines(idea: IdeaStatus) -> list[str]:
    """The idea's briefing, in full."""
    if idea.dropped is None:
        dropped = "; whether it is dropped cannot be told, since a variant's canvas cannot be read"
    else:
        dropped = ", dropped: every variant not split is shelved" if idea.dropped else ""
    out = [f"The idea `{idea.id}`{dropped}"]
    if idea.offer is not None:
        out.extend(f"  {each}" for each in idea.offer.lines())
    if idea.last_act is not None:
        out.append(f"  last act: on {idea.last_act.day}, {', '.join(idea.last_act.what)}")
    goal = _goal_data(idea.goal)
    if idea.goal_why is not None:
        out.append(f"  goal: {idea.goal_why}")
    elif goal is None:
        out.append("  goal: none yet")
    elif None in goal.values():
        unread = [GOAL_WORDS[name] for name, value in goal.items() if value is None]
        out.append(f"  goal: set, but its {positions.joined(unread)} cannot be read")
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
            out.extend(variant.lines())
    drawn = [(v.at.id, v.canvas) for v in idea.variants if v.canvas is not None and v.in_play]
    if drawn:
        out.append("  canvases, of the variants neither shelved nor split:")
        for variant, canvas in drawn:
            out.append(f"    {grid.heading(variant, canvas)}")
            out.extend(f"    {each}" for each in grid.draw(canvas))
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
