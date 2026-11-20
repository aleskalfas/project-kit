"""The gates of the capability's moves and acts, each a predicate over the files and the day of
the act (lean-business DEC-003 points 2 to 4; DEC-002 point 14).

**One predicate, two readers.** A gate answers why it refuses an act, as a list of
refusals, and none where it lets the act through. A command asks it with today's date
before it records the act, and refuses where it answers one; the check asks it with the
day the act was recorded, and reports each refusal as an error. So a gate and the check
never disagree on a fact (DEC-002 point 14). A gate reads no clock: the day is its caller's
(DEC-003 point 1).

**As things stood.** A gate reads the suspensions the cycle's data it is given holds. A
command gives the cycle as it stands; the check gives it as its suspensions stood on the
day of the act (`timeline.stood`; `acts`), so a suspension recorded later never turns an
act a gate let through into one it refuses. A suspension's rules ask the gates with and
without one suspension, so a suspension recorded late contradicts no act already recorded
(`suspensions`).

**What only the act's own day can judge.** A yes and a shortlisting rest on verdicts that
are not stale, and a declaration on a shortlisting that is not stale. A canvas changed
later makes them stale without breaking anything, so the check cannot judge it afterwards,
save where the judgement itself still matches. Each such condition is a gate of its own
(`stale_before`, `stale_verdicts`, `stale_shortlisting`), which a command adds and the check
asks only where it can tell.

The gates, each named for the act it gates:

- the desk stage (DEC-003 point 2): `verdict_order`, `judging`, `yes_content`,
  `stale_before`, `shortlisting`, `stale_verdicts` and `split`;
- an experiment (DEC-003 point 3; DEC-002 points 9 and 10): `declaring`,
  `stale_shortlisting`, `unexplored`, `stopping`, `result` and `deciding`;
- a cycle (DEC-003 point 4; DEC-002 point 11): `planning`, `changing` and `deciding_cycle`;
- the idea's goal (DEC-002 point 3): `setting_goal`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from _lib import fingerprint, ids, readings, timeline
from _lib.fingerprint import STEP_BOXES, STEPS, Shortlisting
from _lib.model import first_planned
from _lib.reading import day
from _lib.timeline import span_text

#: The most days a time box holds, counting its first and its last (DEC-002 point 9).
TIME_BOX_DAYS = 14

#: The fields a declaration needs, by its kind (DEC-002 point 9), besides those every
#: experiment needs.
NEEDS = {
    "generative": ("learn", "stopping-rule", "fit"),
    "evaluative": ("action", "metric", "expected", "source", "control"),
}
EVERY_DECLARATION_NEEDS = ("assumption", "cycle", "start", "end", "authors")

#: The steps judged against the idea's goal (DEC-002 point 3).
JUDGED_AGAINST_THE_GOAL = ("viability", "feasibility")


@dataclass(frozen=True)
class Refusal:
    """Why a gate refuses an act: the place in the subject's file it concerns, as a JSON
    Pointer, and why, in words."""

    pointer: str
    message: str


def _m(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


# --- the desk stage ------------------------------------------------------------------------------


def verdict_order(canvas: Mapping[str, Any]) -> list[Refusal]:
    """Each verdict that stands without a yes on every step before it: a step is judged
    only once each step before it has a yes, and a no clears the verdicts after it."""
    found: list[Refusal] = []
    for position, step in enumerate(STEPS):
        if readings.answer(canvas, step) is None:
            continue
        missing = [s for s in STEPS[:position] if readings.answer(canvas, s) != "yes"]
        if missing:
            found.append(
                Refusal(
                    f"/verdicts/{step}",
                    f"a verdict on {step} stands without a yes on {', '.join(missing)}: each "
                    f"step is judged only once each step before it has a yes, and a no clears "
                    f"the verdicts after it",
                )
            )
    return found


def judging(step: str, goal: Mapping[str, Any] | None) -> list[Refusal]:
    """What any verdict on `step`, a yes or a no, needs of the idea: viability and
    feasibility judge the variant against the goal, so the goal is set first (DEC-002
    point 3)."""
    if step not in JUDGED_AGAINST_THE_GOAL or goal is not None:
        return []
    return [
        Refusal(
            f"/verdicts/{step}",
            f"a verdict on {step} judges the variant against the idea's goal, and the idea has "
            f"none: the goal is set before any variant's viability is judged",
        )
    ]


def yes_content(step: str, canvas: Mapping[str, Any]) -> list[Refusal]:
    """What a yes on `step` needs of the canvas (DEC-003 point 2): each box desirability
    judges holds an entry; viability's revenue streams hold one (`readings.priced`) and the
    estimate's inputs are given; feasibility's traction target names its first stage's
    target."""
    missing: list[str] = []
    if step == "desirability":
        missing = [f"`{box}`" for box in STEP_BOXES[step] if not readings.entries(canvas, box)]
    elif step == "viability":
        if not readings.priced(canvas):
            missing.append("`revenue-streams`")
        if not inputs_given(canvas):
            missing.append("the estimate's inputs, `viability`")
    elif step == "feasibility":
        if _m(_m(canvas.get("traction")).get("first-stage")).get("target") is None:
            missing.append("the first stage's target, `traction`")
    if not missing:
        return []
    return [
        Refusal(
            f"/verdicts/{step}",
            f"a yes on {step} needs {', '.join(missing)}, and the canvas the yes judged holds "
            f"no entry there",
        )
    ]


def inputs_given(canvas: Mapping[str, Any]) -> bool:
    """Whether the canvas gives the estimate's inputs: a set of them that names more than
    its side."""
    sets = [s for s in _list(canvas.get("viability")) if isinstance(s, Mapping)]
    return any(key != "side" for inputs in sets for key in inputs)


def stale_before(step: str, canvas: Mapping[str, Any], goal: object) -> list[Refusal]:
    """What a yes on `step` needs of the steps before it, which only the yes's own day can
    judge: each has a yes that is not stale."""
    found: list[Refusal] = []
    for before in STEPS[: STEPS.index(step)]:
        if readings.answer(canvas, before) != "yes":
            found.append(
                Refusal(f"/verdicts/{step}", f"a yes on {step} needs a yes on {before} first")
            )
        elif fingerprint.check_verdict(before, canvas, goal).stale:
            found.append(_stale_verdict(before))
    return found


def shortlisting(canvas: Mapping[str, Any]) -> list[Refusal]:
    """What a shortlisting needs of the verdicts: a yes on all three steps, since a no
    withdraws it (DEC-003 point 2)."""
    missing = [s for s in STEPS if readings.answer(canvas, s) != "yes"]
    if not missing:
        return []
    return [
        Refusal(
            "/outcome",
            f"a shortlisting needs a yes on all three steps, and the variant has none on "
            f"{', '.join(missing)}",
        )
    ]


def stale_verdicts(canvas: Mapping[str, Any], goal: object) -> list[Refusal]:
    """What a shortlisting needs, which only its own day can judge: none of the verdicts it
    rests on is stale."""
    return [
        _stale_verdict(step)
        for step in STEPS
        if readings.answer(canvas, step) == "yes"
        and fingerprint.check_verdict(step, canvas, goal).stale
    ]


def split(variant: str, named: Sequence[tuple[int, Mapping[str, Any]]]) -> list[Refusal]:
    """What a split of the variant whose id is `variant` needs of the variants it names
    (DEC-002 point 5; DEC-003 point 2): each is another variant, which names this one as
    the variant it comes from. `named` holds each canvas the split names that exists, with
    the place of its name among the variants the outcome lists. A name that finds no canvas
    is not judged here: its lookup reports it."""
    found: list[Refusal] = []
    for index, canvas in named:
        pointer = f"/outcome/into/{index}"
        into = canvas.get("id")
        if into == variant:
            found.append(
                Refusal(
                    pointer,
                    f"the variant is split into itself, `{variant}`: a split variant is final, "
                    f"and goes on only in the other variants it is split into",
                )
            )
            continue
        comes = ids.parse_ref(canvas.get("comes-from"), ids.CANVAS)
        if comes is None or comes.id != variant:
            found.append(
                Refusal(
                    pointer,
                    f"the variant is split into `{into}`, which does not name `{variant}` as "
                    f"the variant it comes from",
                )
            )
    return found


def _stale_verdict(step: str) -> Refusal:
    judged = (
        "the model or the boxes it judged"
        if step == "desirability"
        else "the model, the canvas or the goal it judged"
    )
    return Refusal(
        f"/verdicts/{step}/fingerprint",
        f"the verdict on {step} is stale, and nothing new rests on a stale verdict: {judged} "
        f"changed since it was given",
    )


# --- an experiment -------------------------------------------------------------------------------


def declaring(
    experiment: Mapping[str, Any],
    on: date,
    *,
    cycle: Mapping[str, Any] | None,
    canvas: Mapping[str, Any] | None,
    rests_on: Shortlisting | None,
) -> list[Refusal]:
    """Why the declaring gate refuses `experiment`, declared on `on` in `cycle`, on an
    assumption of the variant whose canvas is `canvas`, resting on the shortlisting
    `rests_on` (DEC-003 points 3 and 7; DEC-002 point 9). A command passes the shortlisting
    the canvas keeps now; the check passes the one the declaration recorded. Where `cycle`
    or `canvas` is None, what needs it is another finding's to report, such as a reference
    that names nothing.

    - every field its kind needs, and at least one estimate;
    - a time box of fourteen days at most, ending no earlier than it starts, and starting
      no earlier than `on`;
    - an expected range whose low is no higher than its high;
    - its cycle open on `on`: its window, under the suspensions `cycle` holds, not ended;
    - a shortlisted variant: the declaration rests on a shortlisting recorded no later than
      `on`, the variant was neither shelved nor split before `on`, and where the shortlisting
      the canvas keeps now was recorded before `on`, it is the one the declaration rests on,
      since it stood that day.

    A day the cycle was suspended is the suspension rules' to refuse, since it holds no act
    (`suspensions`). The variant explored by the cycle is `unexplored`'s, which holds for a
    draft too, and the shortlisting not stale is `stale_shortlisting`'s."""
    found: list[str] = []
    kind = experiment.get("kind")
    needs = (*EVERY_DECLARATION_NEEDS, *NEEDS.get(str(kind), ()))
    missing = [f"`{key}`" for key in needs if experiment.get(key) in (None, [], {}, "")]
    if missing:
        found.append(
            f"it was declared without {', '.join(missing)}, which a {kind} declaration needs"
        )
    if not [e for e in _list(experiment.get("estimates")) if isinstance(e, Mapping)]:
        found.append("it was declared without an estimate, made alone before the declaration")
    start, end = day(experiment.get("start")), day(experiment.get("end"))
    if start is not None and end is not None:
        held = (end - start).days + 1
        if held < 1:
            found.append(f"its time box ends on {end}, before it starts, on {start}")
        elif held > TIME_BOX_DAYS:
            found.append(f"its time box holds {held} days, more than {TIME_BOX_DAYS}")
    if start is not None and start < on:
        found.append(f"its time box starts on {start}, before the day it was declared, {on}")
    span = _m(_m(experiment.get("expected")).get("range"))
    low, high = span.get("low"), span.get("high")
    if _number(low) and _number(high) and low > high:
        found.append(f"its expected range runs from {low} to {high}, its low above its high")
    if cycle is not None:
        window = timeline.cycle_window(cycle)
        if window is not None and window.end is not None and on > window.end:
            found.append(
                f"it was declared on {on}, after its cycle's window ended on {window.end}: an "
                f"experiment is declared only in an open cycle"
            )
    if canvas is not None:
        found.extend(_rests_on(on, canvas, rests_on))
    return [Refusal("/declared", message) for message in found]


def _rests_on(on: date, canvas: Mapping[str, Any], rests_on: Shortlisting | None) -> list[str]:
    variant = canvas.get("id")
    outcome = _m(canvas.get("outcome"))
    kind, settled = outcome.get("kind"), day(outcome.get("when"))
    if kind in ("shelved", "split") and settled is not None and settled < on:
        return [
            f"it was declared on {on}, on an assumption of `{variant}`, which was {kind} on "
            f"{settled}: an experiment is declared only on a shortlisted variant"
        ]
    if rests_on is None:
        return [
            f"it rests on no shortlisting of `{variant}`: an experiment is declared only on a "
            f"shortlisted variant"
        ]
    if rests_on.when > on:
        return [
            f"it rests on a shortlisting of `{variant}` recorded on {rests_on.when}, after the "
            f"day it was declared, {on}"
        ]
    standing = fingerprint.shortlisting(canvas)
    # Fingerprints taken under different forms cannot be compared, which the form's own
    # finding reports, so then the days alone tell the two shortlistings apart.
    comparable = standing is not None and standing.fingerprint.form == rests_on.fingerprint.form
    if (
        standing is not None
        and standing.when < on
        and (standing != rests_on if comparable else standing.when != rests_on.when)
    ):
        return [
            f"it rests on a shortlisting of `{variant}` other than the one that stood on the day "
            f"it was declared, {on}: the canvas keeps one recorded on {standing.when}, and the "
            f"declaration names one recorded on {rests_on.when}"
        ]
    return []


def stale_shortlisting(canvas: Mapping[str, Any], goal: object) -> list[Refusal]:
    """What the declaring gate needs, which only the declaration's own day can judge: the
    variant's shortlisting stands and is not stale (DEC-003 point 7)."""
    if _m(canvas.get("outcome")).get("kind") != "shortlisted":
        return [
            Refusal(
                "/declared",
                f"`{canvas.get('id')}` is not shortlisted: an experiment is declared only on a "
                f"shortlisted variant",
            )
        ]
    if fingerprint.check_shortlisting(canvas, goal).stale:
        return [
            Refusal(
                "/declared",
                f"the shortlisting of `{canvas.get('id')}` is stale: the canvas or the goal "
                f"changed since, so the variant is judged and shortlisted again first",
            )
        ]
    return []


def unexplored(experiment: Mapping[str, Any], cycle: Mapping[str, Any]) -> list[Refusal]:
    """Whether `experiment` tests an assumption of a variant its cycle, `cycle`, does not
    explore, which no experiment does, declared or not (DEC-002 point 11)."""
    reference = ids.parse_ref(experiment.get("assumption"), ids.ASSUMPTIONS)
    if reference is None:
        return []
    variant = ids.qualifier(reference.id)
    if variant in explored(cycle):
        return []
    return [
        Refusal(
            "/assumption",
            f"it tests an assumption of `{variant}`, which its cycle, `{cycle.get('id')}`, does "
            f"not explore",
        )
    ]


def explored(cycle: Mapping[str, Any]) -> list[str]:
    """The ids of the variants a cycle's plan explores."""
    found = (ids.parse_ref(v, ids.CANVAS) for v in _list(cycle.get("variants")))
    return [reference.id for reference in found if reference is not None]


def stopping(
    experiment: Mapping[str, Any], on: date, cycle: Mapping[str, Any] | None
) -> list[Refusal]:
    """Why recording a generative experiment's stopping rule reached on `on` is refused: it
    is recorded only on a declared experiment, while its time box runs, under the
    suspensions `cycle` holds (DEC-002 point 10). Before its time box starts the experiment
    has not run, and after it ends it is due already."""
    if not isinstance(experiment.get("declared"), Mapping):
        return [Refusal("/stopped", "its stopping rule is recorded, but it was never declared")]
    box = timeline.experiment_time_box(experiment, cycle)
    if box is None:
        return []
    if box.start is None or on < box.start:
        return [
            Refusal(
                "/stopped",
                f"its stopping rule was reached on {on}, before its time box started, as its "
                f"cycle's suspensions work it out: {span_text(box)}",
            )
        ]
    if box.end is not None and on > box.end:
        return [
            Refusal(
                "/stopped",
                f"its stopping rule was reached on {on}, after its time box ended on {box.end}: "
                f"a stopping rule ends an experiment before its time box does",
            )
        ]
    return []


def result(
    experiment: Mapping[str, Any], on: date, cycle: Mapping[str, Any] | None
) -> list[Refusal]:
    """Why recording `experiment`'s result on `on` is refused: it is recorded only on a
    declared experiment, and a measurement is recorded as spoiled only where a suspension
    `cycle` holds ran through its time box (DEC-002 point 10). Where `cycle` is None, the
    reference's to report, nothing tells."""
    if not isinstance(experiment.get("declared"), Mapping):
        return [Refusal("/result", "its result is recorded, but it was never declared")]
    if _m(experiment.get("result")).get("spoiled") is not True or cycle is None:
        return []
    box = timeline.experiment_time_box(experiment, cycle)
    if box is None or timeline.ran_through(box, cycle):
        return []
    return [
        Refusal(
            "/result/spoiled",
            f"it is recorded as spoiled, but no suspension of its cycle ran through its time "
            f"box, {span_text(box)}: a measurement is spoiled only by a suspension its time box "
            f"ran through",
        )
    ]


def deciding(
    experiment: Mapping[str, Any], on: date, cycle: Mapping[str, Any] | None
) -> list[Refusal]:
    """Why deciding `experiment` on `on` is refused (DEC-003 point 3): its result is
    recorded, no later than `on`; it was declared; and its time box ended before `on`, under
    the suspensions `cycle` holds, unless it is generative and its stopping rule was reached
    by `on`, within its time box. A day its cycle was suspended is the suspension rules' to
    refuse."""
    found: list[Refusal] = []
    recorded = experiment.get("result")
    if not isinstance(recorded, Mapping):
        found.append(
            Refusal(
                "/decision",
                "it is decided without its result: deciding needs the result and a next action",
            )
        )
    else:
        when = day(recorded.get("when"))
        if when is not None and when > on:
            found.append(
                Refusal(
                    "/result", f"its result was recorded on {when}, after its decision, on {on}"
                )
            )
    if not isinstance(experiment.get("declared"), Mapping):
        found.append(Refusal("/decision", "it is decided, but it was never declared"))
        return found
    box = timeline.experiment_time_box(experiment, cycle)
    if box is None:
        return found
    ended = box.end is not None and on > box.end
    stopped = day(_m(experiment.get("stopped")).get("when"))
    early = (
        experiment.get("kind") == "generative"
        and stopped is not None
        and stopped <= on
        and box.start is not None
        and box.start <= stopped
        and (box.end is None or stopped <= box.end)
    )
    if not ended and not early:
        where = "has not started" if box.start is None else f"ends on {box.end}"
        rule = (
            ""
            if experiment.get("kind") == "evaluative"
            else ", and no stopping rule was reached within it by then"
        )
        found.append(
            Refusal(
                "/decision",
                f"it was decided on {on}, but its time box {where}, as its cycle's suspensions "
                f"work it out{rule}",
            )
        )
    return found


# --- a cycle -------------------------------------------------------------------------------------


def planning(
    cycle: Mapping[str, Any],
    on: date,
    *,
    goal: Mapping[str, Any] | None,
    others: Sequence[Mapping[str, Any]],
) -> list[Refusal]:
    """Why planning `cycle` on `on` is refused, in an idea whose goal is `goal` and whose
    other cycles are `others` (DEC-002 points 3 and 11): the goal is set before the idea's
    first cycle, and the next cycle is planned only once the last is decided, so no other
    cycle planned by `on` is undecided then. A cycle decided on `on` leaves the next to be
    planned that day, at its review. Each variant shortlisted is the command's to read when
    it plans, and a key result for each variant the plan's own invariant."""
    found: list[Refusal] = []
    if goal is None:
        found.append(
            Refusal(
                "/planned",
                "it was planned in an idea with no goal: the goal is set before the idea's "
                "first cycle",
            )
        )
    for other in others:
        planned = first_planned(other)
        if planned is None or planned > on:
            continue
        decided = day(_m(other.get("review")).get("when"))
        if decided is not None and decided <= on:
            continue
        still = "is undecided" if decided is None else f"was decided only on {decided}"
        found.append(
            Refusal(
                "/planned/first",
                f"it was planned on {on}, while `{other.get('id')}`, planned on {planned}, was "
                f"undecided: it {still}, and the next cycle is planned once the last is decided",
            )
        )
    return found


def changing(cycle: Mapping[str, Any], on: date) -> list[Refusal]:
    """Why changing `cycle`'s plan on `on` is refused: a plan is frozen once its window
    starts, under the suspensions `cycle` holds (DEC-002 point 11). A window has started on
    its first day, since the day is the unit (DEC-003 points 1 and 4), so a plan changes
    only on a day before it."""
    window = timeline.cycle_window(cycle)
    if window is None or window.start is None or on < window.start:
        return []
    return [
        Refusal(
            "/planned",
            f"its plan was last changed on {on}, and its window started on {window.start}: a "
            f"plan changes only before its window's first day, and is frozen from it",
        )
    ]


def deciding_cycle(
    cycle: Mapping[str, Any],
    on: date,
    *,
    winning: Mapping[str, Any] | None,
    evidence: Sequence[Mapping[str, Any]],
) -> list[Refusal]:
    """Why deciding `cycle` on `on` is refused, `winning` being the canvas of the variant
    its review names and `evidence` the experiments it names, where they resolve (DEC-003
    point 4): each key result's reach recorded; a winning variant the cycle explored,
    neither shelved nor split before `on` for persevere or pivot; for a pivot, at least one
    experiment decided by `on`; and its window ended before `on`, under the suspensions
    `cycle` holds."""
    found: list[Refusal] = []
    review = _m(cycle.get("review"))
    named = ids.parse_ref(review.get("winning"), ids.CANVAS)
    winner = named.id if named is not None else None
    decision = review.get("decision")
    if winner is not None and winner not in explored(cycle):
        found.append(
            Refusal(
                "/review/winning", f"the winning variant, `{winner}`, is not one the cycle explored"
            )
        )
    results = _list(_m(cycle.get("objective")).get("key-results"))
    reached = _list(review.get("reached"))
    if len(reached) != len(results):
        found.append(
            Refusal(
                "/review/reached",
                f"it records what {_plural(len(reached), 'key result')} reached, and the "
                f"objective has {len(results)}",
            )
        )
    if winning is not None and decision in ("persevere", "pivot"):
        outcome = _m(winning.get("outcome"))
        settled = day(outcome.get("when"))
        if outcome.get("kind") in ("shelved", "split") and settled is not None and settled < on:
            found.append(
                Refusal(
                    "/review/decision",
                    f"it decides to {decision} for `{winner}`, which was {outcome.get('kind')} "
                    f"on {settled}, before the decision: those outcomes are final, so only a "
                    f"pause is open",
                )
            )
    decided = [day(_m(e.get("decision")).get("when")) for e in evidence]
    if decision == "pivot" and not any(d is not None and d <= on for d in decided):
        found.append(
            Refusal(
                "/review/evidence",
                "it pivots on no decided experiment: a pivot names at least one as its evidence",
            )
        )
    window = timeline.cycle_window(cycle)
    if window is not None and (window.end is None or on <= window.end):
        ended = "has no end yet" if window.end is None else f"ends on {window.end}"
        found.append(
            Refusal(
                "/review",
                f"it was decided on {on}, but its window {ended}, as its suspensions work it out",
            )
        )
    return found


# --- the goal ------------------------------------------------------------------------------------


def setting_goal(
    goal: Mapping[str, Any],
    on: date,
    *,
    cycles: Sequence[Mapping[str, Any]],
    previous: Mapping[str, Any] | None = None,
    experiments: Sequence[Mapping[str, Any]] = (),
) -> list[Refusal]:
    """Why setting the idea's goal to `goal` on `on` is refused, in an idea whose cycles are
    `cycles` and whose experiments are `experiments` (DEC-002 point 3):

    - no cycle is planned, running or suspended on `on`: first planned before `on`, and its
      window, under the suspensions its data holds, not ended by `on`. The goal set on the
      day a cycle was first planned may have come first, at the last cycle's review, since
      days have no order within them (DEC-003 point 1);
    - where `previous` is the goal it replaces, it keeps that goal's currency while an
      experiment declared by `on` is undecided then, since that experiment's sums were
      declared in it. The files keep no goal a later one replaced, so the check passes none,
      and the command alone asks this."""
    found: list[Refusal] = []
    for cycle in cycles:
        planned = first_planned(cycle)
        window = timeline.cycle_window(cycle)
        if planned is None or window is None or on <= planned:
            continue
        if window.end is None or on <= window.end:
            found.append(
                Refusal(
                    "",
                    f"the goal was set on {on}, while the cycle `{cycle.get('id')}` was planned, "
                    f"running or suspended: it changes only while none of the idea's cycles is",
                )
            )
    if previous is not None and previous.get("currency") != goal.get("currency"):
        undecided = [
            f"`{e.get('id')}`"
            for e in experiments
            if _on_or_before(_m(e.get("declared")).get("when"), on)
            and not _on_or_before(_m(e.get("decision")).get("when"), on)
        ]
        if undecided:
            found.append(
                Refusal(
                    "/currency",
                    f"the goal's currency changes from {previous.get('currency')} to "
                    f"{goal.get('currency')} on {on}, while {', '.join(undecided)}, declared "
                    f"in the first, {'is' if len(undecided) == 1 else 'are'} undecided: a "
                    f"declared sum keeps the unit it was declared in",
                )
            )
    return found


def _on_or_before(value: object, on: date) -> bool:
    when = day(value)
    return when is not None and when <= on


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"
