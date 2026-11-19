"""The capability's check: what the files of the recorded location break, as one member of
validation (lean-business DEC-002 point 14; COR-055).

It reads the files as they stand, never today's date (COR-055 point 2), and judges what
data can show; the person's judgement of the content is never its question.

- **A broken invariant is an error,** whether a command or a hand edit wrote it: an
  invariant DEC-002 or DEC-003 owns, where the files can show it broken. So what a gate
  keeps, the check shows too.
- **A guideline of the book, or a judgement gone stale, is a warning.** A guideline's
  ranges apply only to a box that holds entries, so a first sketch with blanks draws none.

Where a gate and the check judge the same fact, they read it through one predicate: pricing
(`readings.priced`), where a window and a time box fall (`timeline`), and a suspension's
rules (`suspensions`). Each finding's label is listed, with what it finds, in the
capability's README, "The check".

The references between files (DEC-002 point 7) are resolved here, as errors where one
names nothing, or names another idea's subject, since an idea stands alone.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from _lib import fingerprint, ids, layout, readings, suspensions, timeline
from _lib import location as locations
from _lib.findings import ERROR, WARNING, Finding, at, ordered
from _lib.reading import day
from _lib.root import CONFIG

#: The most days a time box holds, counting its first and its last (DEC-002 point 9).
TIME_BOX_DAYS = 14

#: The book's ranges, each a guideline (DEC-002 point 14).
PROBLEMS = (1, 3)
KEY_METRICS = (3, 5)
HEADLINE_LENGTH = 120

#: The fields a declaration needs, by its kind (DEC-002 point 9), besides those every
#: experiment needs.
NEEDS = {
    "generative": ("learn", "stopping-rule", "fit"),
    "evaluative": ("action", "metric", "expected", "source", "control"),
}
EVERY_DECLARATION_NEEDS = ("assumption", "cycle", "start", "end", "authors")


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
    if where is None:
        return Report([f"no ideas: nothing is recorded, and `{locations.DEFAULT}` is no folder"])
    contents = layout.read(root, where.path)
    found = [Finding(ERROR, stray.rel, stray.why, "layout") for stray in contents.strays]
    pools = Pools.of(contents)
    found.extend(pools.duplicates())
    for idea in contents.ideas.values():
        found.extend(IdeaCheck(idea, pools).run())
    origin = "recorded" if where.recorded else "the default, not recorded yet"
    if not contents.ideas:
        return Report([f"no ideas in `{where.path}` ({origin})"], ordered(found))
    counted = [
        _plural(len(contents.ideas), "idea"),
        _plural(sum(len(i.variants) for i in contents.ideas.values()), "variant"),
        _plural(sum(len(i.experiments) for i in contents.ideas.values()), "experiment"),
        _plural(sum(len(i.cycles) for i in contents.ideas.values()), "cycle"),
    ]
    return Report([f"{', '.join(counted)} in `{where.path}` ({origin})"], ordered(found))


@dataclass(frozen=True)
class Subject:
    """A subject a reference may name: its idea, the file that holds it, and its data."""

    idea: str
    rel: str
    data: Mapping[str, Any]


@dataclass
class Pools:
    """The subjects of the location, by namespace and id, each id with every subject that
    claims it."""

    by: dict[str, dict[str, list[Subject]]] = field(default_factory=dict)

    @staticmethod
    def of(contents: layout.Contents) -> Pools:
        pools = Pools({namespace: {} for namespace in ids.ID_PATTERN})
        for idea in contents.ideas.values():
            for variant in idea.variants.values():
                canvas = variant.canvas.data if variant.canvas is not None else None
                if variant.canvas is not None and canvas is not None:
                    pools.add(
                        ids.CANVAS, canvas.get("id"), Subject(idea.name, variant.canvas.rel, canvas)
                    )
                listed = variant.assumptions.data if variant.assumptions is not None else None
                if variant.assumptions is not None and listed is not None:
                    for entry in _list(listed.get("assumptions")):
                        if isinstance(entry, Mapping):
                            pools.add(
                                ids.ASSUMPTIONS,
                                entry.get("id"),
                                Subject(idea.name, variant.assumptions.rel, entry),
                            )
            for namespace, files in ((ids.EXPERIMENT, idea.experiments), (ids.CYCLE, idea.cycles)):
                for file in files.values():
                    if file.data is not None:
                        pools.add(
                            namespace, file.data.get("id"), Subject(idea.name, file.rel, file.data)
                        )
        return pools

    def add(self, namespace: str, qualified: object, subject: Subject) -> None:
        if isinstance(qualified, str):
            self.by[namespace].setdefault(qualified, []).append(subject)

    def get(self, namespace: str, qualified: str) -> Subject | None:
        found = self.by[namespace].get(qualified)
        return found[0] if found else None

    def duplicates(self) -> list[Finding]:
        found: list[Finding] = []
        for namespace, subjects in self.by.items():
            for qualified, claims in subjects.items():
                files = sorted({claim.rel for claim in claims})
                if len(claims) > 1:
                    found.append(
                        Finding(
                            ERROR,
                            files[0],
                            f"the id `{qualified}` is given {len(claims)} times, in "
                            f"{', '.join(files)}: an id is unique across the location, and a "
                            f"`[{namespace}:...]` reference to it would be ambiguous",
                            "duplicate-id",
                        )
                    )
        return found


# --- an idea --------------------------------------------------------------------------------------


@dataclass
class Experiment:
    rel: str
    own: str
    data: Mapping[str, Any]


@dataclass
class Cycle:
    rel: str
    own: str
    data: Mapping[str, Any]


class IdeaCheck:
    """The findings of one idea's files."""

    def __init__(self, idea: layout.Idea, pools: Pools) -> None:
        self.idea = idea
        self.pools = pools
        self.found: list[Finding] = []
        self.goal = idea.goal.data if idea.goal is not None else None
        self.experiments = [
            Experiment(file.rel, own, file.data)
            for own, file in sorted(idea.experiments.items())
            if file.data is not None
        ]
        self.cycles = [
            Cycle(file.rel, own, file.data)
            for own, file in sorted(idea.cycles.items())
            if file.data is not None
        ]

    def error(self, where: str, message: str, label: str) -> None:
        self.found.append(Finding(ERROR, where, message, label))

    def warn(self, where: str, message: str, label: str) -> None:
        self.found.append(Finding(WARNING, where, message, label))

    def run(self) -> list[Finding]:
        for file in self._files():
            if file.problem is not None:
                label = "unreadable" if file.unreadable else "binding"
                self.error(file.rel, f"it {file.problem}", label)
        for name, variant in sorted(self.idea.variants.items()):
            if variant.canvas is None and variant.assumptions is not None:
                self.error(
                    variant.assumptions.rel,
                    f"the variant `{name}` has assumptions but no canvas, `{layout.CANVAS}`",
                    "layout",
                )
            if variant.canvas is not None and variant.canvas.data is not None:
                CanvasCheck(self, name, variant.canvas.rel, variant.canvas.data).run()
            if variant.assumptions is not None and variant.assumptions.data is not None:
                self._assumptions(name, variant)
        for experiment in self.experiments:
            ExperimentCheck(self, experiment).run()
        for cycle in self.cycles:
            CycleCheck(self, cycle).run()
        self._one_cycle_at_a_time()
        self._goal_held_still()
        return self.found

    def _files(self) -> list[layout.File]:
        files = [self.idea.goal] if self.idea.goal is not None else []
        for variant in self.idea.variants.values():
            files.extend(f for f in (variant.canvas, variant.assumptions) if f is not None)
        files.extend(self.idea.experiments.values())
        files.extend(self.idea.cycles.values())
        return files

    # --- shared readings ---

    def resolve(self, value: object, namespace: str, rel: str, pointer: str) -> Subject | None:
        """The subject a reference names, or None, with an error where it names nothing in
        the location or a subject of another idea. A value that is no reference is the
        shape's to report."""
        found = ids.parse_ref(value, namespace)
        if found is None:
            return None
        if ids.idea_of(found.id) != self.idea.name:
            self.error(
                at(rel, pointer),
                f"it names `{found.id}`, a subject of another idea: an idea stands alone",
                "reference",
            )
            return None
        subject = self.pools.get(namespace, found.id)
        if subject is None:
            self.error(at(rel, pointer), f"it names `{found.id}`, which no file holds", "reference")
        return subject

    def canvas_of(self, variant_id: str) -> Mapping[str, Any] | None:
        subject = self.pools.get(ids.CANVAS, variant_id)
        return subject.data if subject is not None and subject.idea == self.idea.name else None

    def cycle_of(self, experiment: Experiment) -> Mapping[str, Any] | None:
        """The cycle an experiment names, where it resolves within the idea."""
        found = ids.parse_ref(experiment.data.get("cycle"), ids.CYCLE)
        if found is None or ids.idea_of(found.id) != self.idea.name:
            return None
        subject = self.pools.get(ids.CYCLE, found.id)
        return subject.data if subject is not None else None

    def experiments_of(self, cycle_id: str) -> list[Experiment]:
        """The experiments that name the cycle `cycle_id`."""
        named: list[Experiment] = []
        for experiment in self.experiments:
            found = ids.parse_ref(experiment.data.get("cycle"), ids.CYCLE)
            if found is not None and found.id == cycle_id:
                named.append(experiment)
        return named

    def declared_on(self, assumption_id: str) -> bool:
        """Whether a declared experiment names the assumption `assumption_id`."""
        for experiment in self.experiments:
            found = ids.parse_ref(experiment.data.get("assumption"), ids.ASSUMPTIONS)
            if found is not None and found.id == assumption_id and _declared(experiment.data):
                return True
        return False

    def expected_id(self, own: str) -> str:
        return f"{self.idea.name}.{own}"

    # --- assumptions ---

    def _assumptions(self, name: str, variant: layout.Variant) -> None:
        assert variant.assumptions is not None and variant.assumptions.data is not None
        rel = variant.assumptions.rel
        qualifier = self.expected_id(name)
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
                and not self.declared_on(qualified)
            ):
                self.warn(
                    at(rel, f"{pointer}/source/entry"),
                    f"the untested assumption `{qualified}` comes from the entry `{source}`, "
                    f"which its canvas no longer holds",
                    "assumption-source",
                )

    # --- one cycle at a time ---

    def _one_cycle_at_a_time(self) -> None:
        undecided = [c for c in self.cycles if not isinstance(c.data.get("review"), Mapping)]
        if len(undecided) > 1:
            named = ", ".join(f"`{c.data.get('id', c.own)}`" for c in undecided)
            for cycle in undecided:
                self.error(
                    cycle.rel,
                    f"the idea has {len(undecided)} undecided cycles, {named}: it runs one "
                    f"cycle at a time, so the next is planned once the last is decided",
                    "one-cycle",
                )
        spans = [(c, timeline.cycle_window(c.data)) for c in self.cycles]
        for i, (one, first) in enumerate(spans):
            for other, second in spans[i + 1 :]:
                if first is None or second is None or not _windows_meet(first, second):
                    continue
                self.error(
                    other.rel,
                    f"its window, {_span_text(second)}, overlaps the window of "
                    f"`{one.data.get('id', one.own)}`, {_span_text(first)}, as worked out",
                    "one-cycle",
                )

    # --- the goal ---

    def _goal_held_still(self) -> None:
        if self.idea.goal is None or self.goal is None:
            return
        set_on = day(self.goal.get("when"))
        if set_on is None:
            return
        for cycle in self.cycles:
            planned = day(_m(cycle.data.get("planned")).get("when"))
            span = timeline.cycle_window(cycle.data)
            if planned is None or span is None or set_on < planned:
                continue
            if span.end is None or set_on <= span.end:
                self.error(
                    self.idea.goal.rel,
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
        self.id = idea.expected_id(name)

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
        comes = ids.parse_ref(self.data.get("comes-from"), ids.CANVAS)
        if comes is not None and ids.idea_of(comes.id) != self.idea.idea.name:
            self.idea.error(
                at(self.rel, "/comes-from"),
                f"it comes from `{comes.id}`, a variant of another idea: an idea stands alone",
                "reference",
            )

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
        for position, step in enumerate(fingerprint.STEPS):
            if readings.answer(self.data, step) is None:
                continue
            before = fingerprint.STEPS[:position]
            missing = [s for s in before if readings.answer(self.data, s) != "yes"]
            if missing:
                self.idea.error(
                    at(self.rel, f"/verdicts/{step}"),
                    f"a verdict on {step} stands without a yes on {', '.join(missing)}: each "
                    f"step is judged only once each step before it has a yes, and a no clears "
                    f"the verdicts after it",
                    "verdicts",
                )

    def _outcome(self) -> None:
        outcome = _m(self.data.get("outcome"))
        kind = outcome.get("kind")
        if kind == "shortlisted":
            missing = [s for s in fingerprint.STEPS if readings.answer(self.data, s) != "yes"]
            if missing:
                self.idea.error(
                    at(self.rel, "/outcome"),
                    f"the variant is shortlisted without a yes on {', '.join(missing)}: a "
                    f"shortlisting needs a yes on all three steps, and a no withdraws it",
                    "verdicts",
                )
        if kind == "split":
            for index, value in enumerate(_list(outcome.get("into"))):
                subject = self.idea.resolve(value, ids.CANVAS, self.rel, f"/outcome/into/{index}")
                if subject is None:
                    continue
                comes = ids.parse_ref(subject.data.get("comes-from"), ids.CANVAS)
                if comes is None or comes.id != self.id:
                    self.idea.error(
                        at(self.rel, f"/outcome/into/{index}"),
                        f"the variant is split into `{subject.data.get('id')}`, which does not "
                        f"name `{self.id}` as the variant it comes from",
                        "split",
                    )

    def _stale(self) -> None:
        goal = self.idea.goal
        kind = _m(self.data.get("outcome")).get("kind")
        if kind is None:
            for step in fingerprint.STEPS:
                verdict = _m(_m(self.data.get("verdicts")).get(step))
                if not verdict:
                    continue
                self._compare(
                    verdict.get("fingerprint"),
                    lambda form, step=step: fingerprint.of_verdict(step, self.data, goal, form),
                    f"/verdicts/{step}/fingerprint",
                    f"the verdict on {step} is stale: {_judged(step)} changed since, so judge "
                    f"the step again",
                )
        if kind == "shortlisted":
            self._compare(
                _m(self.data.get("outcome")).get("fingerprint"),
                lambda form: fingerprint.of_shortlisting(self.data, goal, form),
                "/outcome/fingerprint",
                "the shortlisting is stale: the canvas or the goal changed since, so no new "
                "experiment rests on it until the variant is judged and shortlisted again",
            )

    def _compare(
        self,
        stored: object,
        taken: Callable[[int], fingerprint.Fingerprint],
        pointer: str,
        stale: str,
    ) -> None:
        outcome = _compared(stored, taken)
        if outcome == fingerprint.DIFFERS:
            self.idea.warn(at(self.rel, pointer), stale, "stale")
        elif outcome is not None and outcome != fingerprint.MATCHES:
            self.idea.error(at(self.rel, pointer), outcome, "fingerprint")

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


# --- an experiment --------------------------------------------------------------------------------


class ExperimentCheck:
    """The findings of one experiment."""

    def __init__(self, idea: IdeaCheck, experiment: Experiment) -> None:
        self.idea = idea
        self.e = experiment
        self.data = experiment.data
        self.rel = experiment.rel
        self.cycle = idea.cycle_of(experiment)

    def run(self) -> None:
        stored, expected = self.data.get("id"), self.idea.expected_id(self.e.own)
        if ids.is_idea_qualified(stored) and stored != expected:
            self.idea.error(
                at(self.rel, "/id"),
                f"its id is `{stored}`, but the file lies where the layout puts `{expected}`",
                "id",
            )
        assumption = self.idea.resolve(
            self.data.get("assumption"), ids.ASSUMPTIONS, self.rel, "/assumption"
        )
        self.idea.resolve(self.data.get("cycle"), ids.CYCLE, self.rel, "/cycle")
        if assumption is not None and self.cycle is not None:
            self._explored(assumption)
        if _declared(self.data):
            self._declaration()
        else:
            for key in ("stopped", "result", "decision"):
                if isinstance(self.data.get(key), Mapping):
                    self.idea.error(
                        at(self.rel, f"/{key}"),
                        f"its {key.replace('stopped', 'stopping rule reached')} is recorded, "
                        f"but the experiment was never declared",
                        "undeclared",
                    )
        self._decision()
        self._within_window()

    def _explored(self, assumption: Subject) -> None:
        assert self.cycle is not None
        qualified = assumption.data.get("id")
        if not isinstance(qualified, str):
            return
        variant = ids.qualifier(qualified)
        explored = {
            r.id
            for r in (ids.parse_ref(v, ids.CANVAS) for v in _list(self.cycle.get("variants")))
            if r is not None
        }
        if variant not in explored:
            self.idea.error(
                at(self.rel, "/assumption"),
                f"it tests an assumption of `{variant}`, which its cycle, "
                f"`{self.cycle.get('id')}`, does not explore",
                "cycle-variants",
            )

    def _declaration(self) -> None:
        declared = _m(self.data.get("declared"))
        outcome = _compared(
            declared.get("fingerprint"), lambda form: fingerprint.of_declaration(self.data, form)
        )
        if outcome == fingerprint.DIFFERS:
            self.idea.error(
                at(self.rel, "/declared/fingerprint"),
                "a declared field changed since it was declared: a declaration is frozen, so "
                "a correction comes as a new experiment",
                "declaration-changed",
            )
        elif outcome is not None and outcome != fingerprint.MATCHES:
            self.idea.error(at(self.rel, "/declared/fingerprint"), outcome, "fingerprint")
        refused = self._refusals(declared)
        for message in refused:
            self.idea.error(at(self.rel, "/declared"), message, "declaration-refused")

    def _refusals(self, declared: Mapping[str, Any]) -> list[str]:
        """Why the declaring gate would have refused the declaration, each in words."""
        found: list[str] = []
        kind = self.data.get("kind")
        needs = (*EVERY_DECLARATION_NEEDS, *NEEDS.get(str(kind), ()))
        missing = [f"`{key}`" for key in needs if self.data.get(key) in (None, [], {}, "")]
        if missing:
            found.append(
                f"it was declared without {', '.join(missing)}, which a {kind} declaration needs"
            )
        if not [e for e in _list(self.data.get("estimates")) if isinstance(e, Mapping)]:
            found.append("it was declared without an estimate, made alone before the declaration")
        start, end, on = (
            day(self.data.get("start")),
            day(self.data.get("end")),
            day(declared.get("when")),
        )
        if start is not None and end is not None:
            held = (end - start).days + 1
            if held < 1:
                found.append(f"its time box ends on {end}, before it starts, on {start}")
            elif held > TIME_BOX_DAYS:
                found.append(f"its time box holds {held} days, more than {TIME_BOX_DAYS}")
        if start is not None and on is not None and start < on:
            found.append(f"its time box starts on {start}, before the day it was declared, {on}")
        # A cycle is open while planned or running (DEC-003 point 7). A day it was suspended
        # is the suspension rules' to refuse, and a review lies after the window's end.
        if on is not None and self.cycle is not None:
            span = timeline.cycle_window(self.cycle)
            if span is not None and span.end is not None and on > span.end:
                found.append(
                    f"it was declared on {on}, after its cycle's window ended on {span.end}: an "
                    f"experiment is declared only in an open cycle"
                )
        if on is not None:
            found.extend(self._rested_on(declared, on))
        return found

    def _rested_on(self, declared: Mapping[str, Any], on: date) -> list[str]:
        """Where the files show that the variant's shortlisting did not stand on the day the
        experiment was declared (DEC-003 point 7): the variant was shelved or split before,
        or the shortlisting the declaration rests on was recorded after."""
        assumption = ids.parse_ref(self.data.get("assumption"), ids.ASSUMPTIONS)
        if assumption is None:
            return []
        variant = ids.qualifier(assumption.id)
        canvas = self.idea.canvas_of(variant)
        if canvas is None:
            return []
        outcome = _m(canvas.get("outcome"))
        kind, settled = outcome.get("kind"), day(outcome.get("when"))
        if settled is None:
            return []
        if kind in ("shelved", "split") and settled < on:
            return [
                f"it was declared on {on}, on an assumption of `{variant}`, which was {kind} on "
                f"{settled}: an experiment is declared only on a shortlisted variant"
            ]
        rested = fingerprint.read(declared.get("rested-on"))
        if kind == "shortlisted" and rested is not None and settled > on:
            if rested == fingerprint.read(outcome.get("fingerprint")):
                return [
                    f"it rests on the shortlisting of `{variant}`, which was recorded on "
                    f"{settled}, after the day it was declared, {on}"
                ]
        return []

    def _decision(self) -> None:
        decision = _m(self.data.get("decision"))
        if not decision:
            return
        decided = day(decision.get("when"))
        result = _m(self.data.get("result"))
        if not result:
            self.idea.error(
                at(self.rel, "/decision"),
                "it is decided without its result: deciding needs the result and a next action",
                "decision-refused",
            )
        recorded = day(result.get("when"))
        if decided is not None and recorded is not None and recorded > decided:
            self.idea.error(
                at(self.rel, "/result"),
                f"its result was recorded on {recorded}, after its decision, on {decided}",
                "decision-refused",
            )
        if decided is None or not _declared(self.data):
            return
        span = timeline.experiment_time_box(self.data, self.cycle)
        if span is None:
            return
        ended = span.end is not None and decided > span.end
        stopped = day(_m(self.data.get("stopped")).get("when"))
        early = self.data.get("kind") == "generative" and stopped is not None and stopped <= decided
        if not ended and not early:
            box = "has not started" if span.start is None else f"ends on {span.end}"
            self.idea.error(
                at(self.rel, "/decision"),
                f"it was decided on {decided}, but its time box {box}, as its cycle's "
                f"suspensions work it out"
                + (
                    ""
                    if self.data.get("kind") == "evaluative"
                    else ", and no stopping rule was reached by then"
                ),
                "decision-refused",
            )

    def _within_window(self) -> None:
        if self.cycle is None:
            return
        box = timeline.experiment_time_box(self.data, self.cycle)
        span = timeline.cycle_window(self.cycle)
        if box is None or span is None or box.start is None or span.start is None:
            return
        outside = box.start < span.start or (
            span.end is not None and box.end is not None and box.end > span.end
        )
        if outside:
            self.idea.warn(
                at(self.rel, "/start"),
                f"its time box, {_span_text(box)}, does not lie within its cycle's window, "
                f"{_span_text(span)}, as worked out",
                "time-box",
            )


# --- a cycle --------------------------------------------------------------------------------------


class CycleCheck:
    """The findings of one cycle."""

    def __init__(self, idea: IdeaCheck, cycle: Cycle) -> None:
        self.idea = idea
        self.c = cycle
        self.data = cycle.data
        self.rel = cycle.rel

    def run(self) -> None:
        stored, expected = self.data.get("id"), self.idea.expected_id(self.c.own)
        if ids.is_idea_qualified(stored) and stored != expected:
            self.idea.error(
                at(self.rel, "/id"),
                f"its id is `{stored}`, but the file lies where the layout puts `{expected}`",
                "id",
            )
        explored = self._variants()
        self._key_results(explored)
        outcome = _compared(
            _m(self.data.get("planned")).get("fingerprint"),
            lambda form: fingerprint.of_plan(self.data, form),
        )
        if outcome == fingerprint.DIFFERS:
            self.idea.error(
                at(self.rel, "/planned/fingerprint"),
                "its plan changed since its fingerprint was taken: a plan is changed only "
                "through the command while the cycle is planned, and is frozen once its window "
                "starts",
                "plan-changed",
            )
        elif outcome is not None and outcome != fingerprint.MATCHES:
            self.idea.error(at(self.rel, "/planned/fingerprint"), outcome, "fingerprint")
        self._suspensions()
        self._review(explored)

    def _variants(self) -> list[str]:
        explored: list[str] = []
        for index, value in enumerate(_list(self.data.get("variants"))):
            self.idea.resolve(value, ids.CANVAS, self.rel, f"/variants/{index}")
            found = ids.parse_ref(value, ids.CANVAS)
            if found is not None:
                explored.append(found.id)
        return explored

    def _key_results(self, explored: list[str]) -> None:
        named: set[str] = set()
        results = _list(_m(self.data.get("objective")).get("key-results"))
        for index, result in enumerate(results):
            if not isinstance(result, Mapping):
                continue
            pointer = f"/objective/key-results/{index}/variant"
            self.idea.resolve(result.get("variant"), ids.CANVAS, self.rel, pointer)
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

    def _suspensions(self) -> None:
        cycle_id = self.data.get("id")
        if not isinstance(cycle_id, str):
            return
        experiments = [(e.rel, e.data) for e in self.idea.experiments_of(cycle_id)]
        goal = (
            (self.idea.idea.goal.rel, self.idea.goal)
            if self.idea.idea.goal is not None and self.idea.goal is not None
            else None
        )
        acts = suspensions.acts_on(self.data, experiments, goal, self.rel)
        for found in suspensions.of_cycle(self.data, acts):
            self.idea.error(
                at(self.rel, f"/suspensions/{found.index}"),
                f"the suspension breaks its rules: {found.message}",
                "suspension",
            )

    def _review(self, explored: list[str]) -> None:
        review = _m(self.data.get("review"))
        if not review:
            return
        decided = day(review.get("when"))
        winning = self.idea.resolve(review.get("winning"), ids.CANVAS, self.rel, "/review/winning")
        found = ids.parse_ref(review.get("winning"), ids.CANVAS)
        winner = found.id if found is not None else None
        decision = review.get("decision")
        if winner is not None and winner not in explored:
            self._refused(
                "/review/winning", f"the winning variant, `{winner}`, is not one the cycle explored"
            )
        results = _list(_m(self.data.get("objective")).get("key-results"))
        reached = _list(review.get("reached"))
        if len(reached) != len(results):
            self._refused(
                "/review/reached",
                f"it records what {_plural(len(reached), 'key result')} reached, and the objective "
                f"has {len(results)}",
            )
        if winning is not None and decision in ("persevere", "pivot"):
            outcome = _m(winning.data.get("outcome"))
            settled = day(outcome.get("when"))
            if (
                outcome.get("kind") in ("shelved", "split")
                and settled
                and decided
                and settled < decided
            ):
                self._refused(
                    "/review/decision",
                    f"it decides to {decision} for `{winner}`, which was {outcome.get('kind')} on "
                    f"{settled}, before the decision: those outcomes are final, so only a pause "
                    f"is open",
                )
        evidence = self._evidence(review)
        if decision == "pivot" and not any(
            on is not None and (decided is None or on <= decided) for on in evidence
        ):
            self._refused(
                "/review/evidence",
                "it pivots on no decided experiment: a pivot names at least one as its evidence",
            )
        span = timeline.cycle_window(self.data)
        if decided is not None and span is not None and (span.end is None or decided <= span.end):
            ended = "has no end yet" if span.end is None else f"ends on {span.end}"
            self._refused(
                "/review",
                f"it was decided on {decided}, but its window {ended}, as its suspensions "
                f"work it out",
            )
        if (
            decision == "persevere"
            and winner is not None
            and readings.met_objective(self.data, winner) is False
        ):
            self.idea.warn(
                at(self.rel, "/review/decision"),
                f"it perseveres, though the winning variant, `{winner}`, missed the objective: "
                f"the method perseveres where the objective was met",
                "persevere-missed",
            )

    def _evidence(self, review: Mapping[str, Any]) -> list[date | None]:
        """The day each experiment the review names as its evidence was decided, None for one
        not decided, each reference resolved."""
        decided: list[date | None] = []
        for index, value in enumerate(_list(review.get("evidence"))):
            subject = self.idea.resolve(
                value, ids.EXPERIMENT, self.rel, f"/review/evidence/{index}"
            )
            if subject is not None:
                decided.append(day(_m(subject.data.get("decision")).get("when")))
        return decided

    def _refused(self, pointer: str, message: str) -> None:
        self.idea.error(at(self.rel, pointer), message, "review-refused")


# --- shared ---------------------------------------------------------------------------------------


def _judged(step: str) -> str:
    """What a verdict on `step` judged, in words."""
    return "the boxes it judged" if step == "desirability" else "the canvas or the goal it judged"


def _declared(experiment: Mapping[str, Any]) -> bool:
    return isinstance(experiment.get("declared"), Mapping)


def _compared(stored: object, taken: Callable[[int], fingerprint.Fingerprint]) -> str | None:
    """What a kept fingerprint compares to: `fingerprint.MATCHES` or `DIFFERS`; None where
    none is kept that reads as one, which the shape reports; else why it cannot be checked,
    in words."""
    try:
        outcome = fingerprint.compare(stored, taken)
    except fingerprint.FingerprintError as exc:
        return f"its fingerprint cannot be checked: {exc}"
    if outcome == fingerprint.UNREADABLE:
        return None
    if outcome == fingerprint.UNKNOWN_FORM:
        form = _m(stored).get("form")
        return (
            f"its fingerprint names the canonical form {form}, which this version of the "
            f"capability does not know, so it cannot be checked"
        )
    return outcome


def _entry_ids(canvas: Mapping[str, Any]) -> set[str]:
    held: set[str] = set()
    for box in fingerprint.BOXES:
        held |= _ids_of(readings.entries(canvas, box))
    return held


def _ids_of(entries: Sequence[Mapping[str, Any]]) -> set[str]:
    return {e["id"] for e in entries if isinstance(e.get("id"), str)}


def _windows_meet(one: timeline.Span, other: timeline.Span) -> bool:
    if one.start is None or other.start is None:
        return False
    one_before_other_ends = other.end is None or one.start <= other.end
    other_before_one_ends = one.end is None or other.start <= one.end
    return one_before_other_ends and other_before_one_ends


def _span_text(span: timeline.Span) -> str:
    if span.start is None:
        return "not started yet"
    if span.end is None:
        return f"from {span.start}, with no end yet"
    return f"{span.start} through {span.end}"
