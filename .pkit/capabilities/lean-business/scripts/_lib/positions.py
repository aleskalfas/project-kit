"""Where each subject of the capability's processes stands, read from its files whenever a
process predicate asks, and what those predicates answer the engine (lean-business DEC-003
points 1 and 2; the process area's README, "The predicate runner").

The engine asks a predicate about one subject, named by its id, and reads one JSON object
from it (COR-033). This module is the one place a subject's position is worked out. The
detection predicates answer from it, and a gate that rests on another subject's position,
such as the experiment's declaring gate on its variant's shortlisting (DEC-003 point 7),
reads that position here too and never works it out again.

- **Reading a subject** (`idea`, `variant`, `variant_in`): the idea's files as the location
  holds them, the ones git sees, as the check reads them (`layout`, `model`).
- **The desk stage** (`desk_stage`): a variant's position, from its outcome and its
  verdicts alone. An outcome outranks the verdicts (DEC-003 point 1). Before one, the
  position is the longest run of the person's standing yes verdicts from the first step
  (`readings.standing`). The detection never reads a box's content or a fingerprint, so a
  stale verdict holds the position (DEC-003 point 2).
- **The desk stage's gates** (`passing`, `shortlisting`, `shelving`): what each move needs,
  through the predicates the check shares (`gates`; DEC-002 point 14). The engine asks a
  gate twice: by `can-move` before the command writes, and by `move` after, against what
  it wrote (the process area's README, "Seam-ordering contract"). So each gate holds of
  the data on both sides of the write.
- **A cycle** (`cycle`, `cycle_in`, `cycle_lifecycle`): a cycle's position, from its
  review, its suspensions and its window as they work it out (DEC-003 points 1 and 4). A
  decision outranks a suspension, and an ongoing suspension, one with no day of resuming,
  outranks the dates. Else the window as worked out (`timeline`) places the cycle planned
  before its first day, running through its last, and in review after it. An experiment's
  predicates read its cycle here too (DEC-003 points 3 and 7): its position, whether it is
  open (`OPEN`), and its suspensions (`suspensions_of`, `ongoing`).
- **The cycle's gates** (`starting_cycle`, `ending_cycle`, `suspending_cycle`,
  `shifting_window`, `resuming_cycle`, `deciding_cycle`). The moves that follow a date or a
  suspension are the script's, gated on the facts the detection reads, so each is closed
  until the data the command writes places the cycle at its target: open at its origin,
  such a move would be a way forward without the person, and lift the wait on a cycle in
  review (DEC-003 point 4; the process area's shape page, "How each wait clears"). A move
  that follows a suspension also needs the suspension to keep its rules, through the
  predicate the check shares (`suspensions.of_cycle`; DEC-002 points 12 and 14). The
  person's moves, resuming and deciding, hold on both sides of the command's write, as the
  desk stage's do: before it, on what the files show; after it, on what it recorded.
- **Answering the engine** (`answer_detection`, `answer_gate`): the subject read from the
  arguments, and the answer printed as the runner reads it.

**Fail closed.** Where the files cannot tell what a predicate is asked, it gives no answer
(`Unreadable`). It says why on standard error and exits non-zero, and the engine reads the
predicate as indeterminate. Such a case is a canvas that does not read, an outcome that is
none of the three, a verdict with no answer, a fingerprint a gate must compare and cannot,
a review whose decision is none of the three, or a window or a suspension whose days do
not read. A plausible default would be a confident wrong answer. A refusal that the files
do show stands, though, beside what cannot be told.

**No clock.** Nothing here reads one. The desk stage reads no day, and the cycle's position
and gates take the day they read, `on`, from their caller (DEC-003 point 1): each predicate
script reads the local date at its entry and passes it in (`as_of`), and the test suite
passes a fixed day.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, TypeVar

from _lib import acts, fingerprint, gates, ids, layout, listing, readings, timeline
from _lib import location as locations
from _lib import suspensions as rules
from _lib.fingerprint import STEPS
from _lib.gates import Refusal
from _lib.model import Cycle as CycleFile
from _lib.model import IdeaModel, Pools
from _lib.reading import day
from _lib.root import project_root
from _lib.timeline import Span, Suspension

# --- the desk stage's states ----------------------------------------------------------------------

SKETCHED = "sketched"
DESIRABLE = "desirable"
VIABLE = "viable"
FEASIBLE = "feasible"
SHORTLISTED = "shortlisted"
SHELVED = "shelved"
SPLIT = "split"

#: The state a variant with no outcome stands in, by how many steps the person's standing
#: yes verdicts run over from the first (DEC-003 point 2).
BY_STANDING = (SKETCHED, DESIRABLE, VIABLE, FEASIBLE)

#: The state each outcome places a variant in, whatever its verdicts say (DEC-002 point 5;
#: DEC-003 point 1).
BY_OUTCOME = {"shortlisted": SHORTLISTED, "shelved": SHELVED, "split": SPLIT}

#: The steps judged against the idea's goal, whose verdicts' fingerprints cover it.
AGAINST_THE_GOAL = gates.JUDGED_AGAINST_THE_GOAL

#: What a yes on each step needs of the canvas, in words, as `gates.yes_content` holds it.
JUDGED = {
    "desirability": "each box desirability judges holds an entry",
    "viability": "the revenue streams hold an entry, and the estimate's inputs are given",
    "feasibility": "the first stage's target is given",
}

# --- the cycle's states ---------------------------------------------------------------------------

PLANNED = "planned"
RUNNING = "running"
SUSPENDED = "suspended"
IN_REVIEW = "in-review"
DECIDED = "decided"

#: The states in which a cycle is open, so that an experiment may be declared in it
#: (DEC-003 point 7).
OPEN = (PLANNED, RUNNING)

#: Each of the cycle's states, in words.
CYCLE_STATE_WORDS = {
    PLANNED: "planned",
    RUNNING: "running",
    SUSPENDED: "suspended",
    IN_REVIEW: "in review",
    DECIDED: "decided",
}

#: The decisions a cycle's review records for its winning variant (DEC-003 point 4).
DECISIONS = ("persevere", "pivot", "pause")

#: The decisions that need the winning variant neither shelved nor split (DEC-003 point 4).
GOING_ON = ("persevere", "pivot")

#: The exit status of a predicate that gives no answer.
NO_ANSWER = 2

#: The longest stretch of a person's words a reason quotes.
QUOTED = 120

_T = TypeVar("_T")


class Unreadable(Exception):
    """The files cannot tell what a predicate is asked, so it gives no answer, and the engine
    reads it as indeterminate."""


@dataclass(frozen=True)
class Position:
    """Where a subject stands: a state of its definition, or None where it stands in none,
    and why. A reason is never blank, since it is all that tells a deliberate "none" from an
    accident (the process area's shape page, "How a classifier's answer is read")."""

    state: str | None
    reason: str


@dataclass(frozen=True)
class Answer:
    """A gate's answer: whether the move may happen, and why."""

    result: bool
    reason: str


def _m(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _quoted(text: str) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= QUOTED else f"{flat[: QUOTED - 1]}…"


def _joined(words: Sequence[str]) -> str:
    if len(words) < 2:
        return "".join(words)
    return f"{', '.join(words[:-1])} and {words[-1]}"


# --- reading a subject ----------------------------------------------------------------------------


def location(root: Path) -> str | None:
    """The location the project reads (`location.for_reading`), or None where nothing records
    one and the default is no folder, so no idea lies anywhere. Raises Unreadable where the
    configuration cannot be read or records a location the rules refuse."""
    try:
        where = locations.for_reading(root)
    except locations.LocationRefused as exc:
        raise Unreadable(f"the location of the ideas cannot be read: {exc}") from exc
    return where.path if where is not None else None


def _contents(root: Path, where: str, name: str) -> layout.Contents:
    try:
        return layout.read(root, where, name)
    except listing.ListingFailed as exc:
        raise Unreadable(f"git cannot list the files of the idea `{name}`: {exc}") from exc
    except layout.IdRefused as exc:
        raise Unreadable(str(exc)) from exc


def idea(root: Path, name: str) -> IdeaModel | None:
    """The idea `name`, an idea's id, as the location holds it: the files of its folder git
    sees. None where the location holds no file of it. Raises Unreadable where the location
    or the files cannot be read."""
    where = location(root)
    if where is None:
        return None
    contents = _contents(root, where, name)
    found = contents.ideas.get(name)
    return IdeaModel(found, Pools.of(contents)) if found is not None else None


@dataclass(frozen=True)
class Variant:
    """A variant, the desk stage's subject: its id, the model of its idea where the idea's
    folder holds a file, where the layout puts its canvas, and the canvas where it lies there.
    `absent` says why there is no canvas, where there is none."""

    id: str
    idea: IdeaModel | None
    rel: str
    canvas: Mapping[str, Any] | None
    absent: str = ""


def _variant_id(subject: str) -> None:
    if not ids.is_idea_qualified(subject):
        raise Unreadable(
            f"`{subject}` is no variant's id: a variant is named `<idea>--<variant>`, each part "
            f"words of lower-case letters and digits joined by single hyphens (DEC-002 point 7)"
        )


def variant_in(model: IdeaModel, subject: str) -> Variant:
    """The variant `subject`, a variant's id, in the idea `model` already read. Raises
    Unreadable where `subject` is no variant's id of that idea, or where its canvas lies in
    its place but does not read."""
    _variant_id(subject)
    if ids.idea_of(subject) != model.name:
        raise Unreadable(f"`{subject}` is no variant of the idea `{model.name}`")
    own = ids.own(subject)
    rel = f"{model.idea.rel}/{layout.VARIANTS}/{own}/{layout.CANVAS}"
    held = model.idea.variants.get(own)
    file = held.canvas if held is not None else None
    if file is None:
        return Variant(subject, model, rel, None, f"no canvas lies at `{rel}`")
    if file.data is None:
        raise Unreadable(f"the canvas at `{rel}` cannot be read: it {file.problem}")
    return Variant(subject, model, rel, file.data)


def variant(root: Path, subject: str) -> Variant:
    """The variant `subject`, a variant's id, as the location holds it. Raises Unreadable
    where `subject` is no variant's id, or where the location, the idea's files or the
    variant's canvas cannot be read."""
    _variant_id(subject)
    where = location(root)
    if where is None:
        return Variant(
            subject,
            None,
            "",
            None,
            f"no idea lies anywhere: nothing records the location, and `{locations.DEFAULT}` "
            f"is no folder",
        )
    name = ids.idea_of(subject)
    rel = layout.path_of(where, "canvas", subject)
    contents = _contents(root, where, name)
    found = contents.ideas.get(name)
    model = IdeaModel(found, Pools.of(contents)) if found is not None else None
    if model is not None:
        read = variant_in(model, subject)
        if read.canvas is not None:
            return read
    folder = rel.rsplit("/", 1)[0]
    return Variant(subject, model, rel, None, _absent(root, rel, contents, "canvas", f"{folder}/"))


def _absent(root: Path, rel: str, contents: layout.Contents, what: str, astray_from: str) -> str:
    """Why no `what` the capability reads lies at `rel`: something lies there that no reader
    of an idea's files sees; or nothing does, where a file whose path starts `astray_from`
    may lie astray instead."""
    if (root / rel).exists():
        return (
            f"no {what} the capability reads lies at `{rel}`: something lies there, but it is "
            f"a link, or a file git ignores, which no reader of an idea's files sees"
        )
    why = f"no {what} lies at `{rel}`"
    astray = [s for s in contents.strays if s.rel.startswith(astray_from)]
    if astray:
        why += f", and `{astray[0].rel}` lies astray in its folder: {astray[0].why}"
    return why


# --- the desk stage ---------------------------------------------------------------------------


def desk_stage(subject: Variant) -> Position:
    """Where the variant `subject` stands in its desk stage (DEC-003 points 1 and 2): the
    state its outcome places it in, whatever its verdicts say; else the state the longest
    run of the person's standing yes verdicts from the first step places it in; None where
    it has no canvas. Raises Unreadable where its outcome, or a verdict the run reaches,
    cannot be read."""
    canvas = subject.canvas
    if canvas is None:
        return Position(
            None,
            f"`{subject.id}` stands in none of the desk stage's states, which start with a "
            f"canvas: {subject.absent}",
        )
    outcome = _outcome(subject)
    if outcome is not None:
        return outcome
    run = _standing(subject)
    return Position(BY_STANDING[len(run)], _why_standing(canvas, run))


def _outcome(subject: Variant) -> Position | None:
    """The position the variant's outcome places it in, or None where it records none."""
    assert subject.canvas is not None
    recorded = subject.canvas.get("outcome")
    if recorded is None:
        return None
    kind = recorded.get("kind") if isinstance(recorded, Mapping) else None
    if not isinstance(kind, str) or kind not in BY_OUTCOME:
        raise Unreadable(
            f"the canvas at `{subject.rel}` records an outcome that is none of shortlisted, "
            f"shelved and split, so where the variant stands cannot be told: an outcome "
            f"outranks the verdicts"
        )
    when = day(_m(recorded).get("when"))
    on = f" on {when}" if when is not None else ""
    if kind == "shortlisted":
        why = f"the person shortlisted the variant{on}, which outranks its verdicts"
    elif kind == "shelved":
        reason = _m(recorded).get("reason")
        said = f": {_quoted(reason)}" if isinstance(reason, str) and reason.strip() else ""
        why = f"the person shelved the variant{on}{said}"
    else:
        into = [
            ref.id
            for ref in (ids.parse_ref(v, ids.CANVAS) for v in _list(_m(recorded).get("into")))
            if ref is not None
        ]
        named = f" into {_joined([f'`{v}`' for v in into])}" if into else ""
        why = f"the person split the variant{on}{named}"
    return Position(BY_OUTCOME[kind], why)


def _standing(subject: Variant) -> tuple[str, ...]:
    """The steps the person's yes stands on (`readings.standing`), once every verdict the
    run reaches is read: a verdict that holds no answer, where the run reaches it, leaves how
    far the run goes untold."""
    assert subject.canvas is not None
    verdicts = subject.canvas.get("verdicts")
    if verdicts is None:
        return ()
    if not isinstance(verdicts, Mapping):
        raise Unreadable(
            f"the canvas at `{subject.rel}` keeps its verdicts as something other than one "
            f"verdict for each step, so how far the person's yes runs cannot be told"
        )
    for step in STEPS:
        if verdicts.get(step) is None:
            break
        answer = readings.answer(subject.canvas, step)
        if answer is None:
            raise Unreadable(
                f"the verdict on {step} at `{subject.rel}` holds no answer, `yes` or `no`, so "
                f"how far the person's yes runs cannot be told"
            )
        if answer == "no":
            break
    return readings.standing(subject.canvas)


def _why_standing(canvas: Mapping[str, Any], run: tuple[str, ...]) -> str:
    if len(run) == len(STEPS):
        return (
            f"the person's yes stands on {_joined(list(run))}, and the variant has no outcome yet"
        )
    following = STEPS[len(run)]
    has = "a no" if readings.answer(canvas, following) == "no" else "no verdict"
    if not run:
        return f"a canvas exists, and desirability has {has}"
    return f"the person's yes stands on {_joined(list(run))}, and {following} has {has}"


# --- the desk stage's gates -------------------------------------------------------------------


def _refused(refusals: Sequence[Refusal]) -> Answer:
    return Answer(False, "; ".join(dict.fromkeys(r.message for r in refusals)))


def _untold(subject: Variant, steps: Sequence[str], *, against_the_goal: bool) -> list[str]:
    """What a gate needs and the files cannot tell: whether each yes on `steps` is stale,
    where its fingerprint cannot be compared with what it judged, which `gates` reads as
    fresh; and the idea's goal, where its file does not read and the move, or a yes it rests
    on, judges the variant against it."""
    assert subject.canvas is not None and subject.idea is not None
    model = subject.idea
    found: list[str] = []
    needs_goal = against_the_goal
    for step in steps:
        if readings.answer(subject.canvas, step) != "yes":
            continue
        if step in AGAINST_THE_GOAL and model.goal_unread:
            needs_goal = True
            continue
        checked = fingerprint.check_verdict(step, subject.canvas, model.goal)
        if checked.outcome == fingerprint.UNREADABLE:
            found.append(f"the verdict on {step} keeps no fingerprint that reads as one")
        elif checked.outcome == fingerprint.UNKNOWN_FORM:
            found.append(
                f"the verdict on {step} keeps a fingerprint of the canonical form "
                f"{checked.form}, which this version of the capability does not know"
            )
        elif checked.outcome == fingerprint.NO_TEXT:
            found.append(f"the fingerprint of the verdict on {step} cannot be taken: {checked.why}")
    if needs_goal and model.goal_unread:
        assert model.idea.goal is not None
        found.append(
            f"the idea's goal at `{model.idea.goal.rel}` cannot be read, and the move judges "
            f"the variant against it"
        )
    return found


def _sifted(subject: Variant, refusals: Sequence[Refusal]) -> list[Refusal]:
    """`refusals`, but where the idea's goal does not read, without those that call a verdict
    judged against the goal stale: compared with no goal, such a verdict reads as changed,
    and whether it is cannot be told (`_untold`). A refusal points into the canvas, and
    `gates` points a stale verdict's at its fingerprint."""
    assert subject.idea is not None
    if not subject.idea.goal_unread:
        return list(refusals)
    compared = {f"/verdicts/{step}/fingerprint" for step in AGAINST_THE_GOAL}
    return [refusal for refusal in refusals if refusal.pointer not in compared]


def _answer(refusals: Sequence[Refusal], untold: Sequence[str], passed: str) -> Answer:
    """The refusals the files show, where there are any; else no answer, where something
    the gate needs cannot be told; else the move passes, for `passed`."""
    if refusals:
        return _refused(refusals)
    if untold:
        raise Unreadable(f"{'; '.join(untold)}: so whether the move may happen cannot be told")
    return Answer(True, passed)


def passing(subject: Variant, step: str) -> Answer:
    """Whether the person's yes on `step` may move the variant into that step's state
    (DEC-003 point 2): the goal set, where the step judges the variant against it
    (`gates.judging`); each box the step judges holding an entry (`gates.yes_content`); and
    a yes that is not stale on each step before it (`gates.stale_before`). A missing link
    between entries is the check's warning, never a refusal. Before the command writes the
    yes and after, the gate reads the same canvas, the yes aside."""
    assert subject.canvas is not None and subject.idea is not None
    model = subject.idea
    before = STEPS[: STEPS.index(step)]
    refusals = [
        *gates.judging(step, model.goal_for_gates()),
        *gates.yes_content(step, subject.canvas),
        *gates.stale_before(step, subject.canvas, model.goal),
    ]
    held: list[str] = []
    if before:
        stale = "neither" if len(before) == 2 else "not"
        held.append(f"the variant has a yes on {_joined(list(before))}, {stale} stale")
    if step in AGAINST_THE_GOAL:
        held.append("the idea's goal is set")
    held.append(JUDGED[step])
    return _answer(
        _sifted(subject, refusals),
        _untold(subject, before, against_the_goal=step in AGAINST_THE_GOAL),
        f"a yes on {step} may stand: {'; '.join(held)}",
    )


def shortlisting(subject: Variant) -> Answer:
    """Whether the person's shortlisting may move the variant into shortlisted, or take its
    fingerprint anew where it is shortlisted already (DEC-003 point 2): a yes on all three
    steps (`gates.shortlisting`), none stale (`gates.stale_verdicts`). The shortlisting
    itself is the move, so the gate reads only the verdicts it rests on, which the command's
    write leaves as they were."""
    assert subject.canvas is not None and subject.idea is not None
    refusals = [
        *gates.shortlisting(subject.canvas),
        *gates.stale_verdicts(subject.canvas, subject.idea.goal),
    ]
    return _answer(
        _sifted(subject, refusals),
        _untold(subject, STEPS, against_the_goal=True),
        f"the variant may be shortlisted: it has a yes on {_joined(list(STEPS))}, none stale",
    )


def shelving(subject: Variant) -> Answer:
    """Whether the person's shelving may move the variant into shelved, from any state but
    shelved and split (DEC-003 point 2): a shelving records its reason. Before the command
    writes it, nothing recorded refuses it, since the variant has no outcome yet or is
    shortlisted. After, the canvas records it shelved with a reason that is not blank."""
    assert subject.canvas is not None
    recorded = subject.canvas.get("outcome")
    if recorded is None:
        return Answer(
            True,
            "the variant may be shelved: it has no outcome yet, and a shelving records its reason",
        )
    kind = recorded.get("kind") if isinstance(recorded, Mapping) else None
    if kind == "shortlisted":
        return Answer(
            True,
            "the variant may be shelved: a shortlisted variant may be, and a shelving records "
            "its reason",
        )
    if kind == "split":
        return Answer(False, "the variant is split, which is final: no split variant is shelved")
    if kind != "shelved":
        raise Unreadable(
            f"the canvas at `{subject.rel}` records an outcome that is none of shortlisted, "
            f"shelved and split, so whether the variant may be shelved cannot be told"
        )
    reason = _m(recorded).get("reason")
    if isinstance(reason, str) and reason.strip():
        return Answer(True, "the canvas records the variant shelved, with its reason")
    return Answer(
        False, "the canvas records the variant shelved without a reason: a shelving says why"
    )


# --- a cycle ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Cycle:
    """A cycle, the subject of the cycle's process: its id, the model of its idea where the
    idea's folder holds a file, where the layout puts its file, and that file where it lies
    there and reads. `absent` says why there is no file, where there is none."""

    id: str
    idea: IdeaModel | None
    rel: str
    held: CycleFile | None
    absent: str = ""

    @property
    def data(self) -> Mapping[str, Any] | None:
        """The cycle's data, or None where no file of it lies in its place."""
        return self.held.data if self.held is not None else None


def _cycle_id(subject: str) -> None:
    if not ids.is_idea_qualified(subject):
        raise Unreadable(
            f"`{subject}` is no cycle's id: a cycle is named `<idea>--<cycle>`, each part "
            f"words of lower-case letters and digits joined by single hyphens (DEC-002 point 7)"
        )


def cycle_in(model: IdeaModel, subject: str) -> Cycle:
    """The cycle `subject`, a cycle's id, in the idea `model` already read, as an
    experiment's predicates find the cycle it names. Raises Unreadable where `subject` is no
    cycle's id of that idea, or where its file lies in its place but does not read."""
    _cycle_id(subject)
    if ids.idea_of(subject) != model.name:
        raise Unreadable(f"`{subject}` is no cycle of the idea `{model.name}`")
    own = ids.own(subject)
    rel = f"{model.idea.rel}/{layout.CYCLES}/{own}{layout.SUFFIX}"
    file = model.idea.cycles.get(own)
    if file is None:
        return Cycle(subject, model, rel, None, f"no cycle's file lies at `{rel}`")
    if file.data is None:
        raise Unreadable(f"the cycle's file at `{rel}` cannot be read: it {file.problem}")
    held = next(each for each in model.cycles if each.own == own)
    return Cycle(subject, model, rel, held)


def cycle(root: Path, subject: str) -> Cycle:
    """The cycle `subject`, a cycle's id, as the location holds it. Raises Unreadable where
    `subject` is no cycle's id, or where the location, the idea's files or the cycle's file
    cannot be read."""
    _cycle_id(subject)
    where = location(root)
    if where is None:
        return Cycle(
            subject,
            None,
            "",
            None,
            f"no idea lies anywhere: nothing records the location, and `{locations.DEFAULT}` "
            f"is no folder",
        )
    name = ids.idea_of(subject)
    rel = layout.path_of(where, "cycle", subject)
    contents = _contents(root, where, name)
    found = contents.ideas.get(name)
    model = IdeaModel(found, Pools.of(contents)) if found is not None else None
    if model is not None:
        read = cycle_in(model, subject)
        if read.held is not None:
            return read
    stem = rel[: -len(layout.SUFFIX)]
    return Cycle(
        subject, model, rel, None, _absent(root, rel, contents, "cycle's file", f"{stem}.")
    )


def _decided(subject: Cycle) -> Position | None:
    """The position the cycle's review places it in, whatever else it holds, or None where
    it records none."""
    assert subject.data is not None
    review = subject.data.get("review")
    if review is None:
        return None
    decision = review.get("decision") if isinstance(review, Mapping) else None
    if not isinstance(decision, str) or decision not in DECISIONS:
        raise Unreadable(
            f"the cycle's file at `{subject.rel}` records a review whose decision is none of "
            f"persevere, pivot and pause, so whether the cycle is decided cannot be told: a "
            f"decision outranks its suspensions and its dates"
        )
    when = day(review.get("when"))
    on = f" on {when}" if when is not None else ""
    winner = ids.parse_ref(review.get("winning"), ids.CANVAS)
    named = f" for `{winner.id}`" if winner is not None else ""
    return Position(
        DECIDED,
        f"the person decided to {decision}{named}{on}, which outranks its suspensions and its "
        f"dates",
    )


def _listed(subject: Cycle) -> list[Suspension]:
    """The cycle's suspensions as its file records them (`timeline.recorded`), once each
    reads as a suspension, and its resumption, where it records one, as a resumption: else
    whether one is ongoing cannot be told."""
    assert subject.data is not None
    written = subject.data.get("suspensions")
    if written is None:
        return []
    if not isinstance(written, list):
        raise Unreadable(
            f"the cycle's file at `{subject.rel}` keeps its suspensions as something other "
            f"than a list of them, so whether one is ongoing cannot be told"
        )
    for index, entry in enumerate(written):
        place = f"the suspension at place {index + 1} of `{subject.rel}`"
        if not isinstance(entry, Mapping):
            raise Unreadable(f"{place} is no suspension, so whether it is ongoing cannot be told")
        resumed = entry.get("resumed")
        if resumed is not None and not isinstance(resumed, Mapping):
            raise Unreadable(
                f"{place} records its resumption as something other than one, so whether it "
                f"is ongoing cannot be told"
            )
    return timeline.recorded(written)


def ongoing(subject: Cycle) -> list[Suspension]:
    """The cycle's ongoing suspensions: those that record no resumption, whatever the day
    (DEC-002 point 12). At most one, where the files keep the rules. Raises Unreadable where
    a suspension cannot be read as one."""
    return [each for each in _listed(subject) if not each.resumed_at_all]


def suspensions_of(subject: Cycle) -> list[Suspension]:
    """The cycle's suspensions, where each day the dates are worked out from reads as a day:
    its first, and its day of resuming where it records one. Raises Unreadable where one does
    not, since `timeline` counts a suspension with no first day as covering nothing, and one
    with no day of resuming as ongoing, and either would place a date the files do not
    give."""
    listed = _listed(subject)
    for each in listed:
        place = f"the suspension at place {each.index + 1} of `{subject.rel}`"
        if each.first_day is None:
            raise Unreadable(
                f"{place} has no first day that reads as a day, so which days it covers "
                f"cannot be told"
            )
        if each.resumed_at_all and each.resumed is None:
            raise Unreadable(
                f"{place} has no day of resuming that reads as a day, so which days it covers "
                f"cannot be told"
            )
    return listed


def window(subject: Cycle) -> Span:
    """Where the cycle's window falls under its suspensions (`timeline.cycle_window`;
    DEC-002 point 12). Its start is None where an ongoing suspension reached it before it
    started, and its end None where one reached it before it ended. Raises Unreadable where
    its declared window, or a day of a suspension, cannot be read."""
    assert subject.data is not None
    suspensions_of(subject)
    span = timeline.cycle_window(subject.data)
    days = _m(subject.data.get("window")).get("days")
    if span is None or not isinstance(days, int) or days < 1:
        raise Unreadable(
            f"the cycle's file at `{subject.rel}` declares no window that reads as one, a first "
            f"day and the days it holds, at least one, so where it falls cannot be told"
        )
    return span


def cycle_lifecycle(subject: Cycle, on: date) -> Position:
    """Where the cycle `subject` stands on the day `on`, today where a predicate asks
    (DEC-003 points 1 and 4): decided where its review records a decision, whatever else it
    holds; else suspended where a suspension is ongoing, whatever its dates; else, by its
    window as its suspensions work it out, planned before the window's first day, running
    through its last, and in review after it. None where it has no file. Raises Unreadable
    where its review, its suspensions or its window cannot be read."""
    if subject.data is None:
        return Position(
            None,
            f"`{subject.id}` stands in none of the cycle's states, which start with its plan: "
            f"{subject.absent}",
        )
    decided = _decided(subject)
    if decided is not None:
        return decided
    current = ongoing(subject)
    if current:
        return Position(SUSPENDED, _why_suspended(current))
    span = window(subject)
    if span.start is None or span.end is None:
        raise Unreadable(
            f"the window of `{subject.id}` has no end as its suspensions work it out, though "
            f"none is ongoing, so where it stands cannot be told"
        )
    moved = ", as its suspensions work it out" if _listed(subject) else ""
    if on < span.start:
        return Position(
            PLANNED,
            f"its plan is recorded, and its window starts on {span.start}{moved}, after today, "
            f"{on}",
        )
    if on <= span.end:
        return Position(
            RUNNING,
            f"its window runs from {span.start} through {span.end}{moved}, and holds today, "
            f"{on}, with no suspension ongoing",
        )
    return Position(
        IN_REVIEW,
        f"its window ended on {span.end}{moved}, before today, {on}, and no decision is recorded",
    )


def _why_suspended(current: Sequence[Suspension]) -> str:
    first = current[0]
    since = f" from {first.first_day}" if first.first_day is not None else ""
    more = f", with {len(current) - 1} more at once" if len(current) > 1 else ""
    return (
        f"a suspension{since} is ongoing{more}, with no day of resuming, which outranks the "
        f"cycle's dates: none of its days count toward the window"
    )


def _not(position: Position, target: str) -> str:
    """Why a cycle at `position` is not at `target`, in words."""
    stands = (
        f"stands {CYCLE_STATE_WORDS[position.state]}"
        if position.state is not None
        else "stands in none of its states"
    )
    return f"the cycle {stands}, not {CYCLE_STATE_WORDS[target]}: {position.reason}"


def _span_words(suspension: Suspension) -> str:
    if suspension.resumed_at_all:
        return f"from {suspension.first_day} until {suspension.resumed}"
    return f"from {suspension.first_day}, ongoing"


# --- the cycle's gates ------------------------------------------------------------------------


def _by_dates(subject: Cycle, on: date, target: str, passed: str) -> Answer:
    """Whether the cycle stands at `target` on the day `on`, as its detection reads it: the
    gate of a move the dates make, on the facts the detection reads (DEC-003 point 4)."""
    position = cycle_lifecycle(subject, on)
    if position.state == target:
        return Answer(True, f"{passed}: {position.reason}")
    return Answer(False, _not(position, target))


def starting_cycle(subject: Cycle, on: date) -> Answer:
    """Whether the dates move the cycle from planned to running on `on`: its window, as its
    suspensions work it out, has started and not ended, no suspension is ongoing, and no
    decision is recorded. So the gate is closed while the cycle is planned, and no command
    takes the move."""
    return _by_dates(subject, on, RUNNING, "the cycle's window has started")


def ending_cycle(subject: Cycle, on: date) -> Answer:
    """Whether the dates move the cycle from running into review on `on`: its window, as its
    suspensions work it out, ended before `on`, no suspension is ongoing, and no decision is
    recorded. So the gate is closed while the cycle runs, and no command takes the move."""
    return _by_dates(subject, on, IN_REVIEW, "the cycle's window has ended")


def suspending_cycle(subject: Cycle, on: date) -> Answer:
    """Whether the person's recorded suspension moves the cycle into suspended, from running
    or from review (DEC-003 point 4): a suspension is ongoing, no decision is recorded, and
    the ongoing suspension keeps its rules (`suspensions.of_cycle`). Before the command
    records the suspension the gate is closed, so that a cycle in review still waits on the
    person. The command validates the suspension through the rules' predicate before it
    writes, and asks the engine to move after."""
    position = cycle_lifecycle(subject, on)
    if position.state != SUSPENDED:
        return Answer(False, _not(position, SUSPENDED))
    return _kept(
        subject,
        ongoing(subject),
        f"the person recorded a suspension that keeps its rules: {position.reason}",
    )


def shifting_window(subject: Cycle, on: date) -> Answer:
    """Whether a suspension already over, recorded late, takes the cycle from review back to
    running (DEC-003 point 4): its window, as its suspensions now work it out, holds `on`,
    no suspension is ongoing, no decision is recorded, and the suspension recorded last
    keeps its rules, contradicting no act already recorded, such as the goal set at the
    review. Before the command records the suspension the gate is closed, as the cycle is in
    review then."""
    position = cycle_lifecycle(subject, on)
    if position.state != RUNNING:
        return Answer(False, _not(position, RUNNING))
    listed = _listed(subject)
    if not listed:
        return Answer(
            False,
            f"no suspension is recorded, and only an absence already over moves a cycle's "
            f"window on, back from its review: {position.reason}",
        )
    last = max(listed, key=rules.recorded_order)
    return _kept(
        subject,
        [last],
        f"the suspension recorded last, {_span_words(last)}, moved the window on, and keeps its "
        f"rules: {position.reason}",
    )


def resuming_cycle(subject: Cycle, on: date) -> Answer:
    """Whether the person's resumption may move the cycle from suspended to running
    (DEC-003 point 4). Before the command records it, the cycle is suspended, with no
    decision recorded. After, no suspension is ongoing, the suspension last by its first
    day, the one the cycle was suspended by, has a day of resuming that keeps its rules
    (`suspensions.of_cycle`), and the window, falling later by the days the suspension
    covered, still holds `on`."""
    position = cycle_lifecycle(subject, on)
    if position.state == SUSPENDED:
        return Answer(
            True,
            f"the cycle may resume: {position.reason}; resuming records the day it resumed, "
            f"which its rules hold no earlier than the suspension's first day and no later "
            f"than the day it is recorded",
        )
    if position.state in (None, DECIDED):
        return Answer(False, _not(position, RUNNING))
    resumed = [each for each in _listed(subject) if each.resumed_at_all]
    if not resumed:
        return Answer(
            False, f"the cycle was never suspended, so it resumes from nothing: {position.reason}"
        )
    last = max(resumed, key=lambda each: (each.first_day or date.min, each.index))
    refused: list[Refusal] = []
    if position.state != RUNNING:
        refused.append(
            Refusal(
                f"/suspensions/{last.index}/resumed",
                f"it resumed on {last.resumed}, and {_not(position, RUNNING)}; the definition "
                f"declares no move from `{SUSPENDED}` to `{position.state}`",
            )
        )
    return _kept(
        subject,
        [last],
        f"the cycle resumed on {last.resumed}, a day its rules allow: {position.reason}",
        refused,
    )


def deciding_cycle(subject: Cycle, on: date) -> Answer:
    """Whether the person's decision may move the cycle from review to decided (DEC-003
    point 4). Before the command records the review, the cycle is in review: its window
    ended before `on`, no suspension is ongoing, and nothing is decided. After, the review
    records a decision of the three, with its reasons, who decided and when, and passes the
    review's gate as the check asks it, on the day it was recorded, with the suspensions as
    they stood then (`gates.deciding_cycle`, through `acts.as_stood`): each key result's
    reach recorded, a winning variant the cycle explored, neither shelved nor split for
    persevere or pivot, a decided experiment as a pivot's evidence, and the window ended."""
    assert subject.data is not None and subject.idea is not None and subject.held is not None
    review = subject.data.get("review")
    if review is None:
        position = cycle_lifecycle(subject, on)
        if position.state != IN_REVIEW:
            return Answer(False, f"{_not(position, IN_REVIEW)}; so no decision is open")
        return Answer(
            True,
            f"the cycle may be decided: {position.reason}; the review records what each key "
            f"result reached, the winning variant among those the cycle explored, and the "
            f"person's decision for it, with its reasons",
        )
    if not isinstance(review, Mapping):
        raise Unreadable(
            f"the cycle's file at `{subject.rel}` keeps its review as something other than "
            f"one, so whether the cycle may be decided cannot be told"
        )
    refusals = _review_recorded(review)
    judged = [act for act in acts.of_cycle(subject.idea, subject.held) if act.pointer == "/review"]
    for act in judged:
        refusals.extend(acts.as_stood(act))
    untold = _untold_window(subject)
    unread_evidence = _unread_evidence(subject, review)
    if unread_evidence and any(r.pointer == "/review/evidence" for r in refusals):
        refusals = [r for r in refusals if r.pointer != "/review/evidence"]
        untold.extend(unread_evidence)
    untold.extend(_unread_winner(subject, review))
    winner = ids.parse_ref(review.get("winning"), ids.CANVAS)
    return _answer(
        refusals,
        untold,
        f"the review records the person's decision on {day(review.get('when'))} to "
        f"{review.get('decision')} for `{winner.id if winner is not None else ''}`, with its "
        f"reasons, and its gate lets it through: each key result's reach is recorded, the "
        f"winning variant is one the cycle explored, and the window ended before the decision",
    )


def _said(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _review_recorded(review: Mapping[str, Any]) -> list[Refusal]:
    """What a review needs recorded beside what its gate judges (DEC-003 point 4): one
    decision of the three, its reasons, the winning variant, and who decided and when."""
    found: list[Refusal] = []
    decision = review.get("decision")
    if not isinstance(decision, str) or decision not in DECISIONS:
        found.append(
            Refusal(
                "/review/decision", "the review records no decision of persevere, pivot and pause"
            )
        )
    if not _said(review.get("reasons")):
        found.append(Refusal("/review/reasons", "the review records no reasons for its decision"))
    if ids.parse_ref(review.get("winning"), ids.CANVAS) is None:
        found.append(Refusal("/review/winning", "the review names no winning variant"))
    if not _said(review.get("by")):
        found.append(Refusal("/review/by", "the review does not say who decided"))
    if day(review.get("when")) is None:
        found.append(
            Refusal(
                "/review/when",
                "the review records no day it was decided, so its gate cannot be asked of it",
            )
        )
    return found


def _unread_file(model: IdeaModel, namespace: str, qualified: str) -> layout.File | None:
    """The file of the idea's subject `qualified`, a variant's canvas or an experiment, where
    it lies in its place but does not read."""
    if ids.idea_of(qualified) != model.name:
        return None
    own = ids.own(qualified)
    if namespace == ids.CANVAS:
        held = model.idea.variants.get(own)
        file = held.canvas if held is not None else None
    else:
        file = model.idea.experiments.get(own)
    return file if file is not None and file.data is None else None


def _unread_winner(subject: Cycle, review: Mapping[str, Any]) -> list[str]:
    """Where a decision to persevere or pivot needs the winning variant neither shelved nor
    split, and its canvas lies in its place but does not read."""
    assert subject.idea is not None
    winner = ids.parse_ref(review.get("winning"), ids.CANVAS)
    if review.get("decision") not in GOING_ON or winner is None:
        return []
    file = _unread_file(subject.idea, ids.CANVAS, winner.id)
    if file is None:
        return []
    return [
        f"the winning variant's canvas at `{file.rel}` cannot be read, and a decision to "
        f"{review.get('decision')} needs the variant neither shelved nor split"
    ]


def _unread_evidence(subject: Cycle, review: Mapping[str, Any]) -> list[str]:
    """Each experiment a pivot names as its evidence whose file lies in its place but does
    not read, so whether it was decided cannot be told."""
    assert subject.idea is not None
    if review.get("decision") != "pivot":
        return []
    found: list[str] = []
    for value in _list(review.get("evidence")):
        reference = ids.parse_ref(value, ids.EXPERIMENT)
        file = _unread_file(subject.idea, ids.EXPERIMENT, reference.id) if reference else None
        if file is not None:
            found.append(
                f"the experiment at `{file.rel}`, which the pivot names as its evidence, cannot "
                f"be read, so whether it was decided cannot be told"
            )
    return found


def _untold_window(subject: Cycle) -> list[str]:
    """Why where the cycle's window falls cannot be told, where it cannot: its gates hold
    an act against the window's end."""
    try:
        window(subject)
    except Unreadable as exc:
        return [str(exc)]
    return []


def _kept(
    subject: Cycle,
    judged: Sequence[Suspension],
    passed: str,
    refused: Sequence[Refusal] = (),
) -> Answer:
    """Whether each of `judged`, suspensions of the cycle, keeps its rules, beside what
    `refused` already refuses: each break the predicate the check shares finds at its place
    (`suspensions.of_cycle`), under the acts its suspensions bear on (`acts.bearing_on`),
    as the command that records a suspension refuses one that a break names. Where what the
    rules weigh cannot be read, and nothing is refused, there is no answer."""
    assert subject.data is not None and subject.idea is not None and subject.held is not None
    places = {each.index for each in judged}
    bearing = acts.bearing_on(subject.idea, subject.held)
    refusals = [
        *refused,
        *(
            Refusal(
                f"/suspensions/{found.index}",
                f"the suspension at place {found.index + 1} breaks its rules: {found.message}",
            )
            for found in rules.of_cycle(subject.data, bearing)
            if found.index in places
        ),
    ]
    return _answer(refusals, _untold_rules(subject), passed)


def _untold_rules(subject: Cycle) -> list[str]:
    """What a suspension's rules weigh and the files cannot tell: the cycle's declared
    window, a day of one of its suspensions, and each file of the idea that records acts,
    the goal, an experiment or a cycle, that lies in its place but does not read."""
    assert subject.data is not None and subject.idea is not None
    found: list[str] = []
    if timeline.cycle_window(subject.data) is None:
        found.append(f"the declared window of `{subject.id}` does not read as one")
    for each in _listed(subject):
        place = f"the suspension at place {each.index + 1}"
        if each.first_day is None:
            found.append(f"{place} has no first day that reads as a day")
        if each.recorded is None:
            found.append(f"{place} has no day it was recorded that reads as a day")
        if each.resumed_at_all and (each.resumed is None or each.resumption_recorded is None):
            found.append(f"{place} records its resumption without days that read as days")
    model = subject.idea
    if model.goal_unread and model.idea.goal is not None:
        found.append(f"the idea's goal at `{model.idea.goal.rel}` cannot be read")
    for files in (model.idea.experiments, model.idea.cycles):
        found.extend(f"`{file.rel}` cannot be read" for file in files.values() if file.data is None)
    if not found:
        return []
    return [f"{'; '.join(found)}, and a suspension's rules weigh them"]


# --- answering the engine ---------------------------------------------------------------------


def _subject(argv: Sequence[str], prog: str, what: str) -> str:
    """The subject the engine names: its first argument, before `--json`."""
    parser = argparse.ArgumentParser(prog=prog, description=what)
    parser.add_argument("subject", help="The subject's id, as the process keys it.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Answer with one JSON object, as the engine reads it. It is the only answer there is.",
    )
    return str(parser.parse_args(list(argv)).subject)


def _no_answer(prog: str, exc: Unreadable) -> int:
    print(f"{prog}: {exc}", file=sys.stderr)
    return NO_ANSWER


def answer_detection(
    argv: Sequence[str], prog: str, what: str, classify: Callable[[Path, str], Position]
) -> int:
    """Answer the engine's `classified` detection of the subject `argv` names, as `classify`
    places it from the project's files: `{state, reason}`, or no answer where the files
    cannot tell."""
    subject = _subject(argv, prog, what)
    try:
        position = classify(project_root(), subject)
    except Unreadable as exc:
        return _no_answer(prog, exc)
    print(json.dumps({"state": position.state, "reason": position.reason}))
    return 0


def answer_gate(
    argv: Sequence[str], prog: str, what: str, judge: Callable[[Path, str], Answer]
) -> int:
    """Answer the engine's deterministic gate on the subject `argv` names, as `judge`
    judges it from the project's files: `{result, reason}`, or no answer where the files
    cannot tell."""
    subject = _subject(argv, prog, what)
    try:
        answer = judge(project_root(), subject)
    except Unreadable as exc:
        return _no_answer(prog, exc)
    print(json.dumps({"result": answer.result, "reason": answer.reason}))
    return 0


def desk_stage_of(root: Path, subject: str) -> Position:
    """Where the variant `subject` stands in its desk stage, read from the project at
    `root`."""
    return desk_stage(variant(root, subject))


def desk_gate(judge: Callable[[Variant], Answer]) -> Callable[[Path, str], Answer]:
    """A desk stage's gate, `judge`, asked of the variant a subject's id names. A variant
    with no canvas stands in no state of the desk stage, so no move of it is open."""

    def asked(root: Path, subject: str) -> Answer:
        read = variant(root, subject)
        if read.canvas is None:
            return Answer(
                False,
                f"no move of the desk stage is open to `{subject}`, which stands in none of its "
                f"states without a canvas: {read.absent}",
            )
        return judge(read)

    return asked


def cycle_lifecycle_of(root: Path, subject: str, on: date) -> Position:
    """Where the cycle `subject` stands on the day `on`, read from the project at `root`."""
    return cycle_lifecycle(cycle(root, subject), on)


def cycle_gate(judge: Callable[[Cycle, date], Answer]) -> Callable[[Path, str, date], Answer]:
    """A cycle's gate, `judge`, asked on a day of the cycle a subject's id names. A cycle
    with no file stands in no state of its process, so no move of it is open."""

    def asked(root: Path, subject: str, on: date) -> Answer:
        read = cycle(root, subject)
        if read.held is None:
            return Answer(
                False,
                f"no move of the cycle is open to `{subject}`, which stands in none of its "
                f"states without its file: {read.absent}",
            )
        return judge(read, on)

    return asked


def as_of(asked: Callable[[Path, str, date], _T], on: date) -> Callable[[Path, str], _T]:
    """`asked`, reading the day `on`: today, the local date a predicate script reads where
    it starts, or a fixed day the test suite gives (DEC-003 point 1)."""

    def read(root: Path, subject: str) -> _T:
        return asked(root, subject, on)

    return read
