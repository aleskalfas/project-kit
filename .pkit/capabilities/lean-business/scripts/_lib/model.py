"""The model of an idea's files: its subjects, and the lookups between them (lean-business
DEC-002 points 2 and 7).

It reads what `layout.read` found and answers, and decides nothing: the check turns what a
lookup failed to find into a finding, and a command refuses it.

- **The subjects of a location** (`Pools`): each variant, assumption, experiment and cycle,
  by its namespace and its id, and the namespaces of which the location holds a file. A
  duplicate id is the core's data validation's to report (COR-029 points 3 and 6).
- **An idea** (`IdeaModel`): its goal, its experiments and its cycles, and the lookups
  between its files. A lookup answers with a typed result, so "no reference" and "a
  reference that names nothing" never read alike: `Found`, a subject of the idea;
  `Dangling`, an id no file of its kind holds, which the core's data validation reports;
  `Unheld`, an id of a kind of which the location holds no file, which the core only warns
  of; `Foreign`, a subject of another idea, which an idea never names, since it stands
  alone; and `NoReference`, a value that is no reference into the namespace, which the
  shape reports.
- **Every fingerprint taken again** (`retaken`): each fingerprint the idea's files keep,
  taken over the files as they stand, as a command keeps it when it records each judgement.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from _lib import fingerprint, ids, layout
from _lib.reading import day

#: The goal the gates are given where the goal's file lies in its place but does not read,
#: which is an error of its own: a goal set, whose content cannot be read, so no gate reads
#: the idea as having none.
UNREAD_GOAL: Mapping[str, Any] = {}


@dataclass(frozen=True)
class Subject:
    """A subject a reference may name: its idea, the file that holds it, and its data."""

    idea: str
    rel: str
    data: Mapping[str, Any]


@dataclass
class Pools:
    """The subjects of the location, by namespace and id, each id with every subject that
    claims it, and the namespaces of which the location holds a file that reads."""

    by: dict[str, dict[str, list[Subject]]] = field(default_factory=dict)
    held: set[str] = field(default_factory=set)

    @staticmethod
    def of(contents: layout.Contents) -> Pools:
        pools = Pools({namespace: {} for namespace in ids.ID_PATTERN})
        for idea in contents.ideas.values():
            for variant in idea.variants.values():
                canvas = variant.canvas
                if canvas is not None and canvas.data is not None:
                    pools.held.add(ids.CANVAS)
                    pools.add(
                        ids.CANVAS,
                        canvas.data.get("id"),
                        Subject(idea.name, canvas.rel, canvas.data),
                    )
                listed = variant.assumptions
                if listed is not None and listed.data is not None:
                    pools.held.add(ids.ASSUMPTIONS)
                    for entry in _list(listed.data.get("assumptions")):
                        if isinstance(entry, Mapping):
                            pools.add(
                                ids.ASSUMPTIONS,
                                entry.get("id"),
                                Subject(idea.name, listed.rel, entry),
                            )
            for namespace, files in ((ids.EXPERIMENT, idea.experiments), (ids.CYCLE, idea.cycles)):
                for file in files.values():
                    if file.data is not None:
                        pools.held.add(namespace)
                        pools.add(
                            namespace, file.data.get("id"), Subject(idea.name, file.rel, file.data)
                        )
        return pools

    def add(self, namespace: str, qualified: object, subject: Subject) -> None:
        if isinstance(qualified, str):
            self.by[namespace].setdefault(qualified, []).append(subject)

    def get(self, namespace: str, qualified: str) -> Subject | None:
        """The first subject that claims `qualified` in `namespace`, or None."""
        found = self.by[namespace].get(qualified)
        return found[0] if found else None


# --- what a lookup finds -------------------------------------------------------------------------


@dataclass(frozen=True)
class Found:
    """A subject of the idea the lookup was made in."""

    subject: Subject


@dataclass(frozen=True)
class Dangling:
    """An id that no file of its kind holds, where the location holds files of that kind:
    the core's data validation reports it (COR-029 point 4)."""

    id: str


@dataclass(frozen=True)
class Unheld:
    """An id of a kind of which the location holds no file, which the core's data
    validation only warns of: the commands write each subject before anything refers to
    it."""

    namespace: str
    id: str


@dataclass(frozen=True)
class Foreign:
    """An id of another idea's subject, which no file of an idea names."""

    id: str


@dataclass(frozen=True)
class NoReference:
    """A value that is no reference into the namespace looked in, which the shape
    reports."""


#: What a lookup finds.
Lookup = Found | Dangling | Unheld | Foreign | NoReference


def found(lookup: Lookup) -> Mapping[str, Any] | None:
    """The data of the subject `lookup` found, or None where it found none."""
    return lookup.subject.data if isinstance(lookup, Found) else None


# --- an idea -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Experiment:
    """An experiment's file that reads: where it lies, its own name, and its data."""

    rel: str
    own: str
    data: Mapping[str, Any]


@dataclass(frozen=True)
class Cycle:
    """A cycle's file that reads: where it lies, its own name, and its data."""

    rel: str
    own: str
    data: Mapping[str, Any]


class IdeaModel:
    """One idea's files, and the lookups between them, within the location's `pools`."""

    def __init__(self, idea: layout.Idea, pools: Pools) -> None:
        self.idea = idea
        self.pools = pools
        self.name = idea.name
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

    @property
    def goal_unread(self) -> bool:
        """Whether the idea's goal file lies in its place but does not read, so whether the
        idea has a goal cannot be told."""
        return self.idea.goal is not None and self.goal is None

    def goal_for_gates(self) -> Mapping[str, Any] | None:
        """The goal the gates read whether the idea has one: its goal, or `UNREAD_GOAL`
        where its file does not read."""
        return UNREAD_GOAL if self.goal_unread else self.goal

    def qualified(self, own: str) -> str:
        """The id the layout gives a subject of the idea whose own name is `own`."""
        return ids.qualify(self.name, own)

    def canvases(self) -> list[tuple[str, layout.File, Mapping[str, Any]]]:
        """Each variant's canvas that reads, with the variant's name and its file, by name."""
        return [
            (name, variant.canvas, variant.canvas.data)
            for name, variant in sorted(self.idea.variants.items())
            if variant.canvas is not None and variant.canvas.data is not None
        ]

    def lookup(self, namespace: str, qualified: str) -> Lookup:
        """The subject of `namespace` whose id is `qualified`."""
        if ids.idea_of(qualified) != self.name:
            return Foreign(qualified)
        subject = self.pools.get(namespace, qualified)
        if subject is not None:
            return Found(subject)
        return Dangling(qualified) if namespace in self.pools.held else Unheld(namespace, qualified)

    def resolve(self, value: object, namespace: str) -> Lookup:
        """The subject the reference `value` names in `namespace`."""
        reference = ids.parse_ref(value, namespace)
        if reference is None:
            return NoReference()
        return self.lookup(namespace, reference.id)

    def canvas_of(self, variant: str) -> Lookup:
        """The canvas of the variant whose id is `variant`."""
        return self.lookup(ids.CANVAS, variant)

    def cycle_of(self, experiment: Experiment) -> Lookup:
        """The cycle an experiment names."""
        return self.resolve(experiment.data.get("cycle"), ids.CYCLE)

    def variant_tested(self, experiment: Experiment) -> str | None:
        """The id of the variant whose assumption an experiment names, or None where it
        names none."""
        reference = ids.parse_ref(experiment.data.get("assumption"), ids.ASSUMPTIONS)
        return ids.qualifier(reference.id) if reference is not None else None

    def experiments_of(self, cycle: str) -> list[Experiment]:
        """The experiments that name the cycle whose id is `cycle`."""
        return [e for e in self.experiments if _names(e.data.get("cycle"), ids.CYCLE, cycle)]

    def experiments_on(self, assumption: str) -> list[Experiment]:
        """The experiments that name the assumption whose id is `assumption`."""
        return [
            e
            for e in self.experiments
            if _names(e.data.get("assumption"), ids.ASSUMPTIONS, assumption)
        ]

    def declared_on(self, assumption: str) -> bool:
        """Whether a declared experiment names the assumption whose id is `assumption`."""
        return any(declared(e.data) for e in self.experiments_on(assumption))


def declared(experiment: Mapping[str, Any]) -> bool:
    """Whether an experiment's declaration is recorded."""
    return isinstance(experiment.get("declared"), Mapping)


def first_planned(cycle: Mapping[str, Any]) -> date | None:
    """The day a cycle was first planned, or the day of its plan's last change where its
    file records no first planning, which the shape reports."""
    planned = _mapping(cycle.get("planned"))
    return day(_mapping(planned.get("first")).get("when")) or day(planned.get("when"))


def _names(value: object, namespace: str, qualified: str) -> bool:
    reference = ids.parse_ref(value, namespace)
    return reference is not None and reference.id == qualified


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


# --- every fingerprint taken again ---------------------------------------------------------------


@dataclass(frozen=True)
class Retaken:
    """A fingerprint taken again: the file that keeps it, the keys that lead to it there,
    and what is kept, as a file writes it."""

    rel: str
    path: tuple[str, ...]
    value: Mapping[str, Any]


def retaken(model: IdeaModel) -> list[Retaken]:
    """Every fingerprint the idea's files keep, taken again over the files as they stand,
    as a command keeps it when it records each judgement over them: each verdict's, and each
    standing shortlisting's, over its canvas and the goal; each declaration's `rested-on`,
    the shortlisting its variant keeps now, and then the declaration's own fingerprint over
    what it declared; and each plan's. A fingerprint over data that has no text, such as a
    number that is not finite, is left as it is."""
    found: list[Retaken] = []
    standing: dict[str, fingerprint.Shortlisting] = {}
    for _, file, canvas in model.canvases():
        for step in fingerprint.STEPS:
            if not isinstance(_mapping(canvas.get("verdicts")).get(step), Mapping):
                continue
            taken = _taken(fingerprint.of_verdict, step, canvas, model.goal)
            if taken is not None:
                found.append(Retaken(file.rel, ("verdicts", step, "fingerprint"), taken.as_data()))
        outcome = _mapping(canvas.get("outcome"))
        when = day(outcome.get("when"))
        if outcome.get("kind") != "shortlisted":
            continue
        taken = _taken(fingerprint.of_shortlisting, canvas, model.goal)
        if taken is None:
            continue
        found.append(Retaken(file.rel, ("outcome", "fingerprint"), taken.as_data()))
        if when is not None and isinstance(canvas.get("id"), str):
            standing[canvas["id"]] = fingerprint.Shortlisting(taken, when)
    for experiment in model.experiments:
        if not declared(experiment.data):
            continue
        record = dict(_mapping(experiment.data.get("declared")))
        rests = standing.get(model.variant_tested(experiment) or "")
        if rests is not None:
            record["rested-on"] = rests.as_data()
            found.append(Retaken(experiment.rel, ("declared", "rested-on"), rests.as_data()))
        taken = _taken(fingerprint.of_declaration, {**experiment.data, "declared": record})
        if taken is not None:
            found.append(Retaken(experiment.rel, ("declared", "fingerprint"), taken.as_data()))
    for cycle in model.cycles:
        taken = _taken(fingerprint.of_plan, cycle.data)
        if taken is not None:
            found.append(Retaken(cycle.rel, ("planned", "fingerprint"), taken.as_data()))
    return found


def _taken(
    take: Callable[..., fingerprint.Fingerprint], *covered: object
) -> fingerprint.Fingerprint | None:
    """What `take` takes over `covered`, or None where the covered data has no text."""
    try:
        return take(*covered)
    except fingerprint.FingerprintError:
        return None
