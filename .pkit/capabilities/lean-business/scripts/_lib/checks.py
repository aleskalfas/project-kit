"""The capability's check: what the files of the recorded location break, as one member of
validation (lean-business DEC-002 point 14; COR-055).

It reads the files as they stand, never today's date (COR-055 point 2), and judges what
data can show; the person's judgement of the content is never its question.

- **A broken invariant is an error,** whether a command or a hand edit wrote it: an
  invariant DEC-002 or DEC-003 owns, where the files can show it broken. So what a gate
  keeps, the check shows too.
- **A guideline of the book, or a judgement gone stale, is a warning.** A guideline's
  ranges apply only to a box that holds entries, so a first sketch with blanks draws none.

Where a gate and the check judge the same fact, they read it through one predicate: the
gates themselves (`gates`), each asked with the day its act was recorded; pricing
(`readings.priced`); whether a fingerprint still matches (`fingerprint`); where a window
and a time box fall (`timeline`); and a suspension's rules (`suspensions`). The model of an
idea's files and its lookups are `model`'s, and this module turns what a lookup failed to
find into a finding. Each finding's label is listed, with what it finds, in the
capability's README, "The check".

The shape of each file is the backbone's data validation's, the `data` member of
`pkit validate` (COR-023), and this check judges only what the shapes leave open: a value
of the wrong shape it reads as missing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _lib import fingerprint, gates, ids, layout, listing, model, readings, schemas
from _lib import location as locations
from _lib import suspensions as rules
from _lib.findings import ERROR, WARNING, Finding, at, ordered
from _lib.model import Found, IdeaModel, Lookup, Subject
from _lib.reading import day
from _lib.root import CONFIG
from _lib.timeline import Span, cycle_window, experiment_time_box, span_text

#: The book's ranges, each a guideline (DEC-002 point 14).
PROBLEMS = (1, 3)
KEY_METRICS = (3, 5)
HEADLINE_LENGTH = 120

#: Where the shape of each file is checked, which the summary names.
SHAPE = (
    "the shape of each file is checked by `pkit validate`'s `data` member, or by "
    "`pkit data validate {}`; this check judges what the shapes leave open"
)

#: The goal the gates are given where the goal's file lies in its place but does not read,
#: which is an error of its own: a goal set, whose content cannot be read, so no gate reads
#: the idea as having none.
UNREAD_GOAL: Mapping[str, Any] = {}


@dataclass
class Report:
    """What the check found: summary lines, and the findings, the errors first."""

    summary: list[str]
    findings: list[Finding] = field(default_factory=list)


def _m(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


# --- the location ---------------------------------------------------------------------------------


def check(root: Path) -> Report:
    """Check the ideas of the location the project reads (`location.for_reading`)."""
    try:
        where = locations.for_reading(root)
    except locations.LocationRefused as exc:
        return Report(
            ["the location cannot be read"], [Finding(ERROR, CONFIG, str(exc), "location")]
        )
    path = where.path if where is not None else locations.DEFAULT
    try:
        contents = layout.read(root, where.path) if where is not None else layout.Contents()
        outside = layout.outside(root, path)
    except listing.ListingFailed as exc:
        return Report(
            ["the files cannot be listed"],
            [Finding(ERROR, path, f"git cannot list the files: {exc}", "location")],
        )
    found = [Finding(ERROR, s.rel, s.why, "layout") for s in (*contents.strays, *outside)]
    if where is None:
        summary = f"no ideas: nothing is recorded, and `{locations.DEFAULT}` is no folder"
        return Report([summary], ordered(found))
    pools = model.Pools.of(contents)
    found.extend(_duplicate(d) for d in pools.duplicates())
    for idea in contents.ideas.values():
        found.extend(IdeaCheck(IdeaModel(idea, pools)).run())
    origin = "recorded" if where.recorded else "the default, not recorded yet"
    if not contents.ideas:
        return Report([f"no ideas in `{where.path}` ({origin})"], ordered(found))
    counted = [
        _plural(len(contents.ideas), "idea"),
        _plural(sum(len(i.variants) for i in contents.ideas.values()), "variant"),
        _plural(sum(len(i.experiments) for i in contents.ideas.values()), "experiment"),
        _plural(sum(len(i.cycles) for i in contents.ideas.values()), "cycle"),
    ]
    summary = [f"{', '.join(counted)} in `{where.path}` ({origin})", SHAPE.format(where.path)]
    return Report(summary, ordered(found))


def _duplicate(duplicate: model.Duplicate) -> Finding:
    return Finding(
        ERROR,
        duplicate.files[0],
        f"the id `{duplicate.id}` is given {duplicate.times} times, in "
        f"{', '.join(duplicate.files)}: an id is unique across the location, and a "
        f"`[{duplicate.namespace}:...]` reference to it would be ambiguous",
        "duplicate-id",
    )


# --- an idea --------------------------------------------------------------------------------------


class IdeaCheck:
    """The findings of one idea's files."""

    def __init__(self, idea: IdeaModel) -> None:
        self.model = idea
        self.found: list[Finding] = []

    def error(self, where: str, message: str, label: str) -> None:
        self.found.append(Finding(ERROR, where, message, label))

    def warn(self, where: str, message: str, label: str) -> None:
        self.found.append(Finding(WARNING, where, message, label))

    def refused(self, rel: str, refusals: Sequence[gates.Refusal], label: str) -> None:
        """Each refusal of a gate, as an error with `label` in the file `rel`."""
        for refusal in refusals:
            self.error(at(rel, refusal.pointer), refusal.message, label)

    def run(self) -> list[Finding]:
        for kind, file in self._files():
            if file.problem is not None:
                label = "unreadable" if file.unreadable else "binding"
                self.error(file.rel, f"it {file.problem}", label)
            elif file.data is not None:
                for pointer, value in schemas.unreadable_days(kind, file.data):
                    self.error(
                        at(file.rel, pointer),
                        f"`{value}` is written as a day, `YYYY-MM-DD`, but names no day of the "
                        f"calendar, so no date it bears on can be compared",
                        "day",
                    )
        for name, variant in sorted(self.model.idea.variants.items()):
            if variant.canvas is None and variant.assumptions is not None:
                self.error(
                    variant.assumptions.rel,
                    f"the variant `{name}` has assumptions but no canvas, `{layout.CANVAS}`",
                    "layout",
                )
            if variant.assumptions is not None and variant.assumptions.data is not None:
                self._assumptions(name, variant)
        for name, file, canvas in self.model.canvases():
            CanvasCheck(self, name, file.rel, canvas).run()
        for experiment in self.model.experiments:
            ExperimentCheck(self, experiment).run()
        for cycle in self.model.cycles:
            CycleCheck(self, cycle).run()
        self._one_cycle_at_a_time()
        self._goal_held_still()
        return self.found

    def _files(self) -> list[tuple[str, layout.File]]:
        idea = self.model.idea
        files: list[tuple[str, layout.File]] = [("goal", idea.goal)] if idea.goal else []
        for variant in idea.variants.values():
            for kind, file in (("canvas", variant.canvas), ("assumptions", variant.assumptions)):
                if file is not None:
                    files.append((kind, file))
        files.extend(("experiment", file) for file in idea.experiments.values())
        files.extend(("cycle", file) for file in idea.cycles.values())
        return files

    # --- shared readings ---

    def reference(self, lookup: Lookup, rel: str, pointer: str) -> Subject | None:
        """The subject a lookup found, or None, with an error where the reference names
        nothing in the location or a subject of another idea. A value that is no reference
        is the shape's to report."""
        if isinstance(lookup, Found):
            return lookup.subject
        if isinstance(lookup, model.Foreign):
            self.error(
                at(rel, pointer),
                f"it names `{lookup.id}`, a subject of another idea: an idea stands alone",
                "reference",
            )
        elif isinstance(lookup, model.Dangling):
            self.error(
                at(rel, pointer), f"it names `{lookup.id}`, which no file holds", "reference"
            )
        return None

    def goal_for_gates(self) -> Mapping[str, Any] | None:
        """The goal the gates read whether the idea has one: its goal, or `UNREAD_GOAL`
        where its file does not read."""
        return UNREAD_GOAL if self.model.goal_unread else self.model.goal

    def fingerprint_error(self, rel: str, pointer: str, checked: fingerprint.Checked) -> None:
        """An error where a kept fingerprint cannot be checked at all."""
        if checked.outcome == fingerprint.UNKNOWN_FORM:
            self.error(
                at(rel, pointer),
                f"its fingerprint names the canonical form {checked.form}, which this version "
                f"of the capability does not know, so it cannot be checked",
                "fingerprint",
            )
        elif checked.outcome == fingerprint.NO_TEXT:
            self.error(
                at(rel, pointer), f"its fingerprint cannot be checked: {checked.why}", "fingerprint"
            )

    # --- assumptions ---

    def _assumptions(self, name: str, variant: layout.Variant) -> None:
        assert variant.assumptions is not None and variant.assumptions.data is not None
        rel = variant.assumptions.rel
        qualifier = self.model.qualified(name)
        canvas = variant.canvas.data if variant.canvas is not None else None
        held = _entry_ids(canvas) if canvas is not None else set()
        for index, entry in enumerate(_list(variant.assumptions.data.get("assumptions"))):
            if not isinstance(entry, Mapping):
                continue
            pointer = f"/assumptions/{index}"
            qualified = entry.get("id")
            if ids.is_variant_qualified(qualified) and ids.qualifier(qualified) != qualifier:
                self.error(
                    at(rel, f"{pointer}/id"),
                    f"the id `{qualified}` is not qualified by its variant, `{qualifier}`",
                    "id",
                )
            source = _m(entry.get("source")).get("entry")
            if (
                canvas is not None
                and isinstance(source, str)
                and source not in held
                and isinstance(qualified, str)
                and not self.model.declared_on(qualified)
            ):
                self.warn(
                    at(rel, f"{pointer}/source/entry"),
                    f"the untested assumption `{qualified}` comes from the entry `{source}`, "
                    f"which its canvas no longer holds",
                    "assumption-source",
                )

    # --- one cycle at a time ---

    def _one_cycle_at_a_time(self) -> None:
        cycles = self.model.cycles
        undecided = [c for c in cycles if not isinstance(c.data.get("review"), Mapping)]
        if len(undecided) > 1:
            named = ", ".join(f"`{c.data.get('id', c.own)}`" for c in undecided)
            for cycle in undecided:
                self.error(
                    cycle.rel,
                    f"the idea has {len(undecided)} undecided cycles, {named}: it runs one "
                    f"cycle at a time, so the next is planned once the last is decided",
                    "one-cycle",
                )
        spans = [(c, cycle_window(c.data)) for c in cycles]
        for i, (one, first) in enumerate(spans):
            for other, second in spans[i + 1 :]:
                if first is None or second is None or not _windows_meet(first, second):
                    continue
                self.error(
                    other.rel,
                    f"its window, {span_text(second)}, overlaps the window of "
                    f"`{one.data.get('id', one.own)}`, {span_text(first)}, as worked out",
                    "one-cycle",
                )

    # --- the goal ---

    def _goal_held_still(self) -> None:
        goal_file = self.model.idea.goal
        if goal_file is None or self.model.goal is None:
            return
        set_on = day(self.model.goal.get("when"))
        if set_on is None:
            return
        for cycle in self.model.cycles:
            planned = model.first_planned(cycle.data)
            span = cycle_window(cycle.data)
            # The goal set on the day a cycle was first planned may have come first, at the
            # last cycle's review: days have no order within them (DEC-003 point 1).
            if planned is None or span is None or set_on <= planned:
                continue
            if span.end is None or set_on <= span.end:
                self.error(
                    goal_file.rel,
                    f"the goal was set on {set_on}, while the cycle "
                    f"`{cycle.data.get('id', cycle.own)}` was planned, running or suspended: "
                    f"it changes only while none of the idea's cycles is",
                    "goal-changed",
                )


# --- a canvas -------------------------------------------------------------------------------------


class CanvasCheck:
    """The findings of one variant's canvas."""

    def __init__(self, idea: IdeaCheck, name: str, rel: str, data: Mapping[str, Any]) -> None:
        self.idea = idea
        self.name = name
        self.rel = rel
        self.data = data
        self.id = idea.model.qualified(name)
        self.goal = idea.model.goal

    def run(self) -> None:
        stored = self.data.get("id")
        if ids.is_idea_qualified(stored) and stored != self.id:
            self.idea.error(
                at(self.rel, "/id"),
                f"its id is `{stored}`, but the file lies where the layout puts `{self.id}`",
                "id",
            )
        self._entries()
        self._sides()
        self._verdicts()
        self._outcome()
        self._stale()
        self._guidelines()
        self._links()
        self._comes_from()

    def _refused(self, refusals: Sequence[gates.Refusal]) -> None:
        self.idea.refused(self.rel, refusals, "verdicts")

    def _verdict(self, step: str) -> fingerprint.Checked | None:
        """The verdict on `step` checked against the canvas and the goal as they stand, or
        None where it covers the goal and the goal's file does not read, so nothing tells."""
        if step != "desirability" and self.idea.model.goal_unread:
            return None
        return fingerprint.check_verdict(step, self.data, self.goal)

    def _shortlisting(self) -> fingerprint.Checked | None:
        """The shortlisting checked, or None where the goal's file does not read."""
        if self.idea.model.goal_unread:
            return None
        return fingerprint.check_shortlisting(self.data, self.goal)

    def _entries(self) -> None:
        seen: dict[str, str] = {}
        for box in fingerprint.BOXES:
            for index, entry in enumerate(_list(_m(self.data.get("boxes")).get(box))):
                if not isinstance(entry, Mapping):
                    continue
                qualified = entry.get("id")
                pointer = f"/boxes/{box}/{index}/id"
                if not ids.is_variant_qualified(qualified):
                    continue
                if ids.qualifier(qualified) != self.id:
                    self.idea.error(
                        at(self.rel, pointer),
                        f"the id `{qualified}` is not qualified by its variant, `{self.id}`",
                        "id",
                    )
                if qualified in seen:
                    self.idea.error(
                        at(self.rel, pointer),
                        f"the id `{qualified}` is given twice, at {seen[qualified]} and here",
                        "duplicate-id",
                    )
                else:
                    seen[qualified] = f"/boxes/{box}/{index}"

    def _sides(self) -> None:
        named = [s for s in _list(self.data.get("sides")) if isinstance(s, str)]
        archetype = self.data.get("archetype")
        if archetype == "direct" and named:
            self.idea.error(
                at(self.rel, "/sides"),
                "a direct model names no sides, and this one names some",
                "sides",
            )
        sided = archetype in ("multisided", "marketplace")
        if sided and len(named) < 2:
            self.idea.warn(
                at(self.rel, "/sides"),
                f"a {archetype} model serves more than one side, and this one names {len(named)}",
                "sides-incomplete",
            )
        for box in fingerprint.BOXES:
            unsided = 0
            for index, entry in enumerate(readings.entries(self.data, box)):
                side = entry.get("side")
                if isinstance(side, str) and side not in named:
                    self.idea.error(
                        at(self.rel, f"/boxes/{box}/{index}/side"),
                        f"it names the side `{side}`, which the canvas does not name",
                        "sides",
                    )
                if sided and side is None:
                    unsided += 1
            if unsided:
                self.idea.warn(
                    at(self.rel, f"/boxes/{box}"),
                    f"{'1 entry names' if unsided == 1 else f'{unsided} entries name'} no side, "
                    f"in a model with several",
                    "sides-incomplete",
                )
        seen: set[object] = set()
        sets = [s for s in _list(self.data.get("viability")) if isinstance(s, Mapping)]
        for index, inputs in enumerate(sets):
            side = inputs.get("side")
            pointer = at(self.rel, f"/viability/{index}")
            if not sided and (side is not None or len(sets) > 1):
                self.idea.error(
                    pointer,
                    "a direct model gives one set of inputs, for no side",
                    "sides",
                )
            elif sided and isinstance(side, str) and side not in named:
                self.idea.error(
                    pointer, f"it names the side `{side}`, which the canvas does not name", "sides"
                )
            elif sided and side is None:
                self.idea.warn(
                    pointer, "it names no side, in a model with several", "sides-incomplete"
                )
            if sided and side is not None and side in seen:
                self.idea.error(pointer, f"the side `{side}` is given inputs twice", "sides")
            seen.add(side)

    def _verdicts(self) -> None:
        """The desk gate's conditions the files can show: the verdicts' order, the goal a
        verdict on viability or feasibility was judged against, and what a yes needed of
        the canvas, where the yes still matches the canvas it judged."""
        self._refused(gates.verdict_order(self.data))
        for step in fingerprint.STEPS:
            answer = readings.answer(self.data, step)
            if answer is None:
                continue
            self._refused(gates.judging(step, self.idea.goal_for_gates()))
            checked = self._verdict(step)
            if answer == "yes" and checked is not None and checked.fresh:
                self._refused(gates.yes_content(step, self.data))

    def _outcome(self) -> None:
        outcome = _m(self.data.get("outcome"))
        kind = outcome.get("kind")
        if kind == "shortlisted":
            self._refused(gates.shortlisting(self.data))
            # A shortlisting that still matches was taken over the canvas and the goal as
            # they stand, so a verdict stale now was stale when it was taken.
            checked = self._shortlisting()
            if checked is not None and checked.fresh:
                self._refused(gates.stale_verdicts(self.data, self.goal))
        if kind == "split":
            for index, value in enumerate(_list(outcome.get("into"))):
                pointer = f"/outcome/into/{index}"
                subject = self.idea.reference(
                    self.idea.model.resolve(value, ids.CANVAS), self.rel, pointer
                )
                if subject is None:
                    continue
                comes = ids.parse_ref(subject.data.get("comes-from"), ids.CANVAS)
                if comes is None or comes.id != self.id:
                    self.idea.error(
                        at(self.rel, pointer),
                        f"the variant is split into `{subject.data.get('id')}`, which does not "
                        f"name `{self.id}` as the variant it comes from",
                        "split",
                    )

    def _stale(self) -> None:
        kind = _m(self.data.get("outcome")).get("kind")
        for step in fingerprint.STEPS:
            if not _m(_m(self.data.get("verdicts")).get(step)):
                continue
            pointer = f"/verdicts/{step}/fingerprint"
            checked = self._verdict(step)
            if checked is None:
                continue
            self.idea.fingerprint_error(self.rel, pointer, checked)
            if checked.stale and kind is None:
                self.idea.warn(
                    at(self.rel, pointer),
                    f"the verdict on {step} is stale: {_judged(step)} changed since, so judge "
                    f"the step again",
                    "stale",
                )
        checked = self._shortlisting()
        if kind == "shortlisted" and checked is not None:
            pointer = "/outcome/fingerprint"
            self.idea.fingerprint_error(self.rel, pointer, checked)
            if checked.stale:
                self.idea.warn(
                    at(self.rel, pointer),
                    "the shortlisting is stale: the canvas or the goal changed since, so no new "
                    "experiment rests on it until the variant is judged and shortlisted again",
                    "stale",
                )

    def _guidelines(self) -> None:
        sides: list[object] = [s for s in _list(self.data.get("sides")) if isinstance(s, str)] or [
            None
        ]
        problems = readings.entries(self.data, "problem")
        for side in sides:
            counted = [p for p in problems if side is None or p.get("side") == side]
            if len(counted) > PROBLEMS[1]:
                which = f" for the side `{side}`" if side is not None else ""
                self.idea.warn(
                    at(self.rel, "/boxes/problem"),
                    f"{len(counted)} problems{which}: the method keeps one to three",
                    "guideline",
                )
        metrics = readings.entries(self.data, "key-metrics")
        if metrics and not KEY_METRICS[0] <= len(metrics) <= KEY_METRICS[1]:
            self.idea.warn(
                at(self.rel, "/boxes/key-metrics"),
                f"{_plural(len(metrics), 'key metric')}: the method keeps three to five",
                "guideline",
            )
        for index, entry in enumerate(readings.entries(self.data, "unique-value-proposition")):
            text = entry.get("text")
            if isinstance(text, str) and len(text) > HEADLINE_LENGTH:
                self.idea.warn(
                    at(self.rel, f"/boxes/unique-value-proposition/{index}/text"),
                    f"its headline holds {len(text)} characters: the method keeps it to about "
                    f"{HEADLINE_LENGTH}",
                    "guideline",
                )
        if readings.answer(self.data, "desirability") == "yes" and not readings.priced(self.data):
            self.idea.warn(
                at(self.rel, "/boxes/revenue-streams"),
                "the revenue streams hold no entry, though desirability has a yes: a canvas may "
                "leave boxes blank, but not its pricing",
                "guideline",
            )

    def _links(self) -> None:
        held = {box: _ids_of(readings.entries(self.data, box)) for box in fingerprint.BOXES}
        for index, entry in enumerate(readings.entries(self.data, "problem")):
            pointer = f"/boxes/problem/{index}"
            alternatives = [a for a in _list(entry.get("alternatives")) if isinstance(a, str)]
            if not alternatives:
                self._link(
                    pointer, "the problem names no existing alternative it is framed against"
                )
            for offset, alternative in enumerate(alternatives):
                if alternative not in held["existing-alternatives"]:
                    self._link(
                        f"{pointer}/alternatives/{offset}",
                        f"it names `{alternative}`, which the existing alternatives do not hold",
                    )
        for box, what in (
            ("solution", "solution"),
            ("unique-value-proposition", "value proposition"),
        ):
            for index, entry in enumerate(readings.entries(self.data, box)):
                answered = entry.get("problem")
                if not isinstance(answered, str):
                    self._link(f"/boxes/{box}/{index}", f"the {what} names no problem it answers")
                elif answered not in held["problem"]:
                    self._link(
                        f"/boxes/{box}/{index}/problem",
                        f"it names `{answered}`, which the problems do not hold",
                    )
        for index, entry in enumerate(readings.entries(self.data, "early-adopters")):
            if not [t for t in _list(entry.get("triggers")) if isinstance(t, str)]:
                self._link(
                    f"/boxes/early-adopters/{index}",
                    "the early adopter names no trigger, the event that made such customers switch",
                )
        for index, entry in enumerate(readings.entries(self.data, "key-metrics")):
            if entry.get("step") is None:
                self._link(
                    f"/boxes/key-metrics/{index}",
                    "the key metric names no step of the customer factory it measures",
                )

    def _link(self, pointer: str, message: str) -> None:
        self.idea.warn(at(self.rel, pointer), message, "link")

    def _comes_from(self) -> None:
        """The variant this one comes from (DEC-002 point 4): one it was split from, which
        names it among the variants it went into, or a shelved one whose story it takes up."""
        lookup = self.idea.model.resolve(self.data.get("comes-from"), ids.CANVAS)
        origin = self.idea.reference(lookup, self.rel, "/comes-from")
        if origin is None:
            return
        outcome = _m(origin.data.get("outcome"))
        kind, named = outcome.get("kind"), origin.data.get("id")
        if kind not in ("split", "shelved"):
            self.idea.error(
                at(self.rel, "/comes-from"),
                f"it comes from `{named}`, which is neither split nor shelved: a variant comes "
                f"from one it was split from, or a shelved one whose story it takes up",
                "comes-from",
            )
        elif kind == "split":
            into = [ids.parse_ref(v, ids.CANVAS) for v in _list(outcome.get("into"))]
            if self.id not in {reference.id for reference in into if reference is not None}:
                self.idea.error(
                    at(self.rel, "/comes-from"),
                    f"it comes from `{named}`, which was split into other variants, not this one",
                    "comes-from",
                )


# --- an experiment --------------------------------------------------------------------------------


class ExperimentCheck:
    """The findings of one experiment."""

    def __init__(self, idea: IdeaCheck, experiment: model.Experiment) -> None:
        self.idea = idea
        self.e = experiment
        self.data = experiment.data
        self.rel = experiment.rel
        self.cycle = model.found(idea.model.cycle_of(experiment))

    def run(self) -> None:
        stored, expected = self.data.get("id"), self.idea.model.qualified(self.e.own)
        if ids.is_idea_qualified(stored) and stored != expected:
            self.idea.error(
                at(self.rel, "/id"),
                f"its id is `{stored}`, but the file lies where the layout puts `{expected}`",
                "id",
            )
        lookup = self.idea.model.resolve(self.data.get("assumption"), ids.ASSUMPTIONS)
        assumption = self.idea.reference(lookup, self.rel, "/assumption")
        self.idea.reference(self.idea.model.cycle_of(self.e), self.rel, "/cycle")
        if assumption is not None and self.cycle is not None:
            self.idea.refused(self.rel, gates.unexplored(self.data, self.cycle), "cycle-variants")
        if model.declared(self.data):
            self._declaration()
            self._after()
        else:
            for key in ("stopped", "result", "decision"):
                if isinstance(self.data.get(key), Mapping):
                    self.idea.error(
                        at(self.rel, f"/{key}"),
                        f"its {key.replace('stopped', 'stopping rule reached')} is recorded, "
                        f"but the experiment was never declared",
                        "undeclared",
                    )
        self._within_window()

    def _declaration(self) -> None:
        declared = _m(self.data.get("declared"))
        checked = fingerprint.check_declaration(self.data)
        if checked.stale:
            self.idea.error(
                at(self.rel, "/declared/fingerprint"),
                "a declared field, or the record of the declaration, changed since it was "
                "declared: a declaration is frozen, so a correction comes as a new experiment",
                "declaration-changed",
            )
        self.idea.fingerprint_error(self.rel, "/declared/fingerprint", checked)
        on = day(declared.get("when"))
        if on is None:
            return
        variant = self.idea.model.variant_tested(self.e)
        canvas = model.found(self.idea.model.canvas_of(variant)) if variant else None
        written = declared.get("rested-on")
        rests_on = fingerprint.rested_on(written)
        if written is not None and rests_on is None:
            # It names a shortlisting that does not read whole, which the shape, or the
            # day, reports: what the declaration rested on cannot be told then.
            canvas = None
        refusals = gates.declaring(
            self.data, on, cycle=self.cycle, canvas=canvas, rests_on=rests_on
        )
        self.idea.refused(self.rel, refusals, "declaration-refused")

    def _after(self) -> None:
        """What was recorded on the experiment after its declaration, each held to the gate
        of its act on the day it was recorded."""
        for key, gate, label in (
            ("stopped", gates.stopping, "stop-refused"),
            ("result", gates.result, "result-refused"),
            ("decision", gates.deciding, "decision-refused"),
        ):
            recorded = self.data.get(key)
            on = day(_m(recorded).get("when"))
            if not isinstance(recorded, Mapping) or on is None:
                continue
            self.idea.refused(self.rel, gate(self.data, on, self.cycle), label)

    def _within_window(self) -> None:
        if self.cycle is None:
            return
        box = experiment_time_box(self.data, self.cycle)
        span = cycle_window(self.cycle)
        if box is None or span is None or box.start is None or span.start is None:
            return
        outside = box.start < span.start or (
            span.end is not None and box.end is not None and box.end > span.end
        )
        if outside:
            self.idea.warn(
                at(self.rel, "/start"),
                f"its time box, {span_text(box)}, does not lie within its cycle's window, "
                f"{span_text(span)}, as worked out",
                "time-box",
            )


# --- a cycle --------------------------------------------------------------------------------------


class CycleCheck:
    """The findings of one cycle."""

    def __init__(self, idea: IdeaCheck, cycle: model.Cycle) -> None:
        self.idea = idea
        self.c = cycle
        self.data = cycle.data
        self.rel = cycle.rel

    def run(self) -> None:
        stored, expected = self.data.get("id"), self.idea.model.qualified(self.c.own)
        if ids.is_idea_qualified(stored) and stored != expected:
            self.idea.error(
                at(self.rel, "/id"),
                f"its id is `{stored}`, but the file lies where the layout puts `{expected}`",
                "id",
            )
        explored = self._variants()
        self._key_results(explored)
        checked = fingerprint.check_plan(self.data)
        if checked.stale:
            self.idea.error(
                at(self.rel, "/planned/fingerprint"),
                "its plan changed since its fingerprint was taken: a plan is changed only "
                "through the command while the cycle is planned, and is frozen once its window "
                "starts",
                "plan-changed",
            )
        self.idea.fingerprint_error(self.rel, "/planned/fingerprint", checked)
        self._planning()
        self._suspensions()
        self._review()

    def _variants(self) -> list[str]:
        for index, value in enumerate(_list(self.data.get("variants"))):
            lookup = self.idea.model.resolve(value, ids.CANVAS)
            self.idea.reference(lookup, self.rel, f"/variants/{index}")
        return gates.explored(self.data)

    def _key_results(self, explored: list[str]) -> None:
        named: set[str] = set()
        results = _list(_m(self.data.get("objective")).get("key-results"))
        for index, result in enumerate(results):
            if not isinstance(result, Mapping):
                continue
            pointer = f"/objective/key-results/{index}/variant"
            lookup = self.idea.model.resolve(result.get("variant"), ids.CANVAS)
            self.idea.reference(lookup, self.rel, pointer)
            found = ids.parse_ref(result.get("variant"), ids.CANVAS)
            if found is None:
                continue
            named.add(found.id)
            if found.id not in explored:
                self.idea.error(
                    at(self.rel, pointer),
                    f"the key result names `{found.id}`, which the cycle does not explore",
                    "cycle-variants",
                )
        for variant in explored:
            if variant not in named:
                self.idea.error(
                    at(self.rel, "/objective/key-results"),
                    f"the cycle explores `{variant}`, and no key result names it: each variant a "
                    f"cycle explores has one of its own",
                    "cycle-variants",
                )

    def _planning(self) -> None:
        """The planning command's conditions, on the day the cycle was first planned, and a
        plan frozen once its window started, on the day it last changed."""
        planned = _m(self.data.get("planned"))
        first = model.first_planned(self.data)
        last = day(planned.get("when"))
        if first is not None:
            others = [c.data for c in self.idea.model.cycles if c is not self.c]
            goal = self.idea.goal_for_gates()
            refusals = gates.planning(self.data, first, goal=goal, others=others)
            self.idea.refused(self.rel, refusals, "plan-refused")
        if last is not None and first is not None and last != first:
            self.idea.refused(self.rel, gates.changing(self.data, last), "plan-refused")

    def _suspensions(self) -> None:
        cycle_id = self.data.get("id")
        if not isinstance(cycle_id, str):
            return
        experiments = [(e.rel, e.data) for e in self.idea.model.experiments_of(cycle_id)]
        goal_file, goal = self.idea.model.idea.goal, self.idea.model.goal
        held = (goal_file.rel, goal) if goal_file is not None and goal is not None else None
        acts = rules.acts_on(self.data, experiments, held, self.rel)
        for found in rules.of_cycle(self.data, acts):
            self.idea.error(
                at(self.rel, f"/suspensions/{found.index}"),
                f"the suspension breaks its rules: {found.message}",
                "suspension",
            )

    def _review(self) -> None:
        review = _m(self.data.get("review"))
        if not review:
            return
        lookup = self.idea.model.resolve(review.get("winning"), ids.CANVAS)
        winning = self.idea.reference(lookup, self.rel, "/review/winning")
        evidence: list[Mapping[str, Any]] = []
        for index, value in enumerate(_list(review.get("evidence"))):
            lookup = self.idea.model.resolve(value, ids.EXPERIMENT)
            subject = self.idea.reference(lookup, self.rel, f"/review/evidence/{index}")
            if subject is not None:
                evidence.append(subject.data)
        decided = day(review.get("when"))
        if decided is not None:
            refusals = gates.deciding_cycle(
                self.data,
                decided,
                winning=winning.data if winning is not None else None,
                evidence=evidence,
            )
            self.idea.refused(self.rel, refusals, "review-refused")
        found = ids.parse_ref(review.get("winning"), ids.CANVAS)
        winner = found.id if found is not None else None
        if (
            review.get("decision") == "persevere"
            and winner is not None
            and readings.met_objective(self.data, winner) is False
        ):
            self.idea.warn(
                at(self.rel, "/review/decision"),
                f"it perseveres, though the winning variant, `{winner}`, missed the objective: "
                f"the method perseveres where the objective was met",
                "persevere-missed",
            )


# --- shared ---------------------------------------------------------------------------------------


def _judged(step: str) -> str:
    """What a verdict on `step` judged, in words."""
    return "the boxes it judged" if step == "desirability" else "the canvas or the goal it judged"


def _entry_ids(canvas: Mapping[str, Any]) -> set[str]:
    held: set[str] = set()
    for box in fingerprint.BOXES:
        held |= _ids_of(readings.entries(canvas, box))
    return held


def _ids_of(entries: Sequence[Mapping[str, Any]]) -> set[str]:
    return {e["id"] for e in entries if isinstance(e.get("id"), str)}


def _windows_meet(one: Span, other: Span) -> bool:
    if one.start is None or other.start is None:
        return False
    one_before_other_ends = other.end is None or one.start <= other.end
    other_before_one_ends = one.end is None or other.start <= one.end
    return one_before_other_ends and other_before_one_ends
