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
- **Answering the engine** (`answer_detection`, `answer_gate`): the subject read from the
  arguments, and the answer printed as the runner reads it.

**Fail closed.** Where the files cannot tell what a predicate is asked, it gives no answer
(`Unreadable`). It says why on standard error and exits non-zero, and the engine reads the
predicate as indeterminate. Such a case is a canvas that does not read, an outcome that is
none of the three, a verdict with no answer, or a fingerprint a gate must compare and
cannot. A plausible default would be a confident wrong answer. A refusal that the files do
show stands, though, beside what cannot be told.

**No clock.** The desk stage reads no day, so nothing here reads one.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import fingerprint, gates, ids, layout, listing, readings
from _lib import location as locations
from _lib.fingerprint import STEPS
from _lib.gates import Refusal
from _lib.model import IdeaModel, Pools
from _lib.reading import day
from _lib.root import project_root

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

#: The exit status of a predicate that gives no answer.
NO_ANSWER = 2

#: The longest stretch of a person's words a reason quotes.
QUOTED = 120


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
    astray = [s for s in contents.strays if s.rel.startswith(f"{folder}/")]
    why = f"no canvas lies at `{rel}`"
    if (root / rel).exists():
        why = (
            f"no canvas the capability reads lies at `{rel}`: something lies there, but it is "
            f"a link, or a file git ignores, which no reader of an idea's files sees"
        )
    elif astray:
        why += f", and `{astray[0].rel}` lies astray in its folder: {astray[0].why}"
    return Variant(subject, model, rel, None, why)


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
