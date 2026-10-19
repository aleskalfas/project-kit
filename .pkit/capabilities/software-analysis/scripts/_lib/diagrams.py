"""The analysis's diagrams, drawn from its front matter (DEC-003).

Four diagrams are drawn from the relations the front matter holds (points 3
to 5), each for one analysis (point 6): the one the working tree holds, or,
where the project lists several (DEC-001 point 2), the one the query names. An
actor of another analysis, named with it, such as `core:ACT-developer`, is the
one node drawn from beyond its edge, among the actors, by that id alone:

- **The use-case diagram** — the system's boundary, the use cases in force
  inside it and the actors in force around it. An arrow joins each use case to
  its `actor`, and a line to each of its `other-actors`. With no use case in
  force there is none: actors alone would be a context view (point 4).
- **A journey's flow** — its actor, then its `steps` in their order. The use
  cases of its `relies-on` stand in a group of their own, with no arrow: which
  step relies on which lies in the body, which no tool reads (DEC-001 point 1).
- **The requirement map** — each requirement in force, the use cases and
  journeys in force that list it in their `requirements`, the requirements it
  `refines` and the actors whose need it meets. For one requirement, that
  requirement alone with what it names and what lists it.
- **The chain of use cases** (point 5) — the use cases in force, grouped by
  area, the areas in the order of their numbers, and an arrow from each
  producer a use case's `after` names to that use case: a use case in force of
  the analysis, the use case itself, or the environment, one node beside the
  areas. An arrow from a producer in a later area is dotted. A solid arrow other
  solid arrows imply is left out, as `_lib/chain.py` says. It is drawn where a
  use case in force writes `after`.

- **Only what is in force.** A withdrawn artefact draws nothing, and nor does a
  reference to an artefact the analysis does not hold in force: the check
  reports it. A journey's step keeps its place in the order, drawn by its id
  alone.
- **Neutral, with a text alternative.** Each diagram is a Mermaid `flowchart`
  that opens with its `accTitle` and `accDescr`, and holds no styling: no
  `%%{init}%%` directive, `classDef`, `class`, `style` or `linkStyle` line
  (point 7). A shape tells kinds apart, and an arrow's form tells relations
  apart.
- **The same bytes.** Nodes and edges are sorted, and a node's id is the
  artefact's id with each character outside letters and digits made `_`.
- **Complete, or no answer.** A file of a place a diagram reads that holds no
  artefact of its kind, an artefact there with no id of its kind's shape, or one
  in force whose list a diagram reads that is no list of ids, is no answer, and so
  is, for the chain, a use case in force whose `after` is no list of lists. What
  the diagram would draw cannot be told, so a smaller one would read as true.
  The check says what is wrong with the file.

The analysis is read through the backbone's reading, `pkit friction artefacts
--json` (`backbone.read_analysis`), of the working tree. Nothing is written.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from _lib import chain, met_by, schemas
from _lib.model import (
    ACTOR,
    AFTER,
    ANYWHERE,
    ENVIRONMENT,
    JOURNEY,
    MUST_MEET,
    NOUN,
    OTHER_ACTORS,
    RELIES_ON,
    REQUIREMENT,
    REQUIREMENTS,
    USE_CASE,
    Analysis,
    Artefact,
    identity,
    number_in,
    qualified,
)

#: The version of the document `--json` prints.
SCHEMA_VERSION = 1

#: The subjects that name a diagram rather than an artefact.
USE_CASES = "use-cases"
JOURNEYS = "journeys"
REQUIREMENT_MAP = "requirements"
CHAIN = "chain"
SUBJECTS = (USE_CASES, JOURNEYS, REQUIREMENT_MAP, CHAIN)

#: The front-matter fields a diagram reads, beside `actor` and `requirements`.
STEPS = "steps"
REFINES = "refines"
ACTORS = "actors"

#: The kinds each diagram reads, so a file it cannot read is no answer for it alone.
_READS = {
    USE_CASES: (ACTOR, USE_CASE),
    JOURNEYS: (ACTOR, USE_CASE, JOURNEY),
    REQUIREMENT_MAP: (ACTOR, USE_CASE, JOURNEY, *REQUIREMENTS),
    CHAIN: (USE_CASE,),
}

#: The lists of ids each kind's front matter holds that a diagram reads.
_LISTS = {
    USE_CASE: (OTHER_ACTORS, MUST_MEET),
    JOURNEY: (STEPS, RELIES_ON, MUST_MEET),
    **dict.fromkeys(REQUIREMENTS, (REFINES, ACTORS)),
}


class NoAnswer(Exception):
    """A diagram cannot be drawn in full, or the subject names none; the message says why."""


@dataclass(frozen=True)
class Diagram:
    """One diagram: its id, its title and description (its `accTitle` and `accDescr`),
    and its Mermaid text, without the fence."""

    id: str
    title: str
    description: str
    mermaid: str


def diagrams(
    analysis: Analysis,
    subject: str | None,
    shown_as: Mapping[str, str],
    folder: str | None = ANYWHERE,
) -> list[Diagram]:
    """The diagrams `subject` names: every diagram the analysis has something for when it
    is `None`, the use-case diagram, each journey's flow, the requirement map, the chain
    of use cases, one journey's flow by its id, or one requirement's map by its id.
    `shown_as` is each kind
    of requirement as its heading shows it. Each draws the one analysis in `folder` of the
    location, `None` its top (point 6). Raises NoAnswer when a file the diagrams read
    cannot be read in full, or when `subject` names no diagram."""
    which = _which(subject)
    drawn = _Drawn(analysis, _reads(which), folder, chained=which in (None, CHAIN))
    found: list[Diagram] = []
    if which in (None, USE_CASES):
        found.extend(drawn.use_cases())
    if which in (None, JOURNEYS):
        found.extend(drawn.journey(j) for j in drawn.in_force(JOURNEY))
    if which == JOURNEY:
        found.append(drawn.journey(drawn.named(JOURNEY, str(subject))))
    if which in (None, REQUIREMENT_MAP):
        found.extend(drawn.requirements(shown_as))
    if which == REQUIREMENT:
        found.append(drawn.requirement(drawn.named(REQUIREMENT, str(subject)), shown_as))
    if which in (None, CHAIN):
        found.extend(drawn.chain())
    return found


def _which(subject: str | None) -> str | None:
    """What `subject` asks for: `None` for every diagram, a diagram's name, or
    JOURNEY or REQUIREMENT for one artefact's diagram."""
    if subject is None or subject in SUBJECTS:
        return subject
    if schemas.id_pattern(JOURNEY).match(identity(subject)):
        return JOURNEY
    if schemas.id_pattern(REQUIREMENTS[0]).match(identity(subject)):
        return REQUIREMENT
    raise NoAnswer(
        f"no diagram for {subject!r}: name {', '.join(SUBJECTS)}, a journey's id or a "
        f"requirement's id"
    )


def _reads(which: str | None) -> tuple[str, ...]:
    if which is None:
        return tuple(dict.fromkeys(k for kinds in _READS.values() for k in kinds))
    if which == JOURNEY:
        return _READS[JOURNEYS]
    if which == REQUIREMENT:
        return _READS[REQUIREMENT_MAP]
    return _READS[which]


class _Drawn:
    """The analysis as the diagrams read it: each artefact of the kinds read, held to
    what a diagram needs of it, and those in force by id."""

    def __init__(
        self,
        analysis: Analysis,
        kinds: Sequence[str],
        folder: str | None = ANYWHERE,
        *,
        chained: bool = False,
    ) -> None:
        def drawn(path: str) -> bool:
            return folder == ANYWHERE or analysis.folders.get(path) == folder

        unread = sorted(
            {
                *(s.path for s in analysis.strays if s.kind in kinds and drawn(s.path)),
                *(p for p in analysis.unreadable if analysis.files.get(p) in kinds and drawn(p)),
            }
        )
        if unread:
            raise NoAnswer(
                f"{', '.join(unread)} cannot be read as "
                f"{'an artefact of its place' if len(unread) == 1 else 'artefacts of their places'}"
                f", so what the diagram draws cannot be told; `pkit analysis validate` says why"
            )
        read = sorted(
            (a for a in analysis.artefacts if a.kind in kinds and drawn(a.path)), key=_order
        )
        for artefact in read:
            _readable(artefact, chained=chained)
        self.analysis = analysis
        self.folder = folder
        self.read = read
        self.by_id: dict[str, Artefact] = {}
        self.foreign: dict[str, Artefact] = {}
        for artefact in read:
            if not artefact.withdrawn:
                self.by_id.setdefault(identity(str(artefact.id)), artefact)

    def in_force(self, *kinds: str) -> list[Artefact]:
        return [a for a in self.by_id.values() if a.kind in kinds]

    def held(self, artefact_id: Any, *kinds: str) -> Artefact | None:
        """The artefact in force of one of `kinds` that `artefact_id` names, if any. An
        actor of another analysis, named with it, is the one node drawn from beyond the
        analysis's edge, by that id alone, so no diagram depends on another analysis's
        files (point 6)."""
        if not isinstance(artefact_id, str):
            return None
        if ACTOR in kinds and qualified(artefact_id)[0] is not None:
            return self.foreign.setdefault(
                artefact_id,
                Artefact(ACTOR, artefact_id, "", artefact_id, False, {}, {}),
            )
        found = self.by_id.get(identity(artefact_id))
        return found if found is not None and found.kind in kinds else None

    def named(self, kind: str, subject: str) -> Artefact:
        """The artefact in force `subject` names, of `kind` or, for REQUIREMENT, of any
        kind of requirement; NoAnswer when the analysis holds none in force."""
        kinds = REQUIREMENTS if kind == REQUIREMENT else (kind,)
        found = self.held(subject, *kinds)
        if found is not None:
            return found
        noun = REQUIREMENT if kind == REQUIREMENT else NOUN[kind]
        withdrawn = any(
            a.kind in kinds and identity(str(a.id)) == identity(subject) for a in self.read
        )
        if withdrawn:
            raise NoAnswer(
                f"{noun} {subject} is withdrawn, and a diagram draws only what is in force"
            )
        raise NoAnswer(f"no {noun} {subject} in the analysis")

    # --- the use-case diagram -----------------------------------------------------------

    def use_cases(self) -> list[Diagram]:
        use_cases = self.in_force(USE_CASE)
        if not use_cases:
            return []
        edges: set[str] = set()
        for use_case in use_cases:
            actor = self.held(use_case.fields.get("actor"), ACTOR)
            if actor is not None:
                edges.add(f"{_id(actor)} --> {_id(use_case)}")
            for other in _ids(use_case, OTHER_ACTORS):
                taking_part = self.held(other, ACTOR)
                if taking_part is not None and taking_part is not actor:
                    edges.add(f"{_id(taking_part)} --- {_id(use_case)}")
        actors = sorted([*self.in_force(ACTOR), *self.foreign.values()], key=_order)
        lines = [_node(a) for a in actors]
        lines.append('subgraph boundary["The system"]')
        lines.extend(f"  {_node(u)}" for u in use_cases)
        lines.append("end")
        description = (
            f"The system's boundary holds {_count(len(use_cases), 'use case')}, and "
            f"{_count(len(actors), 'actor')} stand{'s' if len(actors) == 1 else ''} around it. "
            "An arrow joins each use case to the actor whose goal it is, and a line joins it "
            "to each other actor who takes part."
        )
        return [_diagram(USE_CASES, "The use cases and their actors", description, lines, edges)]

    # --- a journey's flow ---------------------------------------------------------------

    def journey(self, journey: Artefact) -> Diagram:
        steps = _ids(journey, STEPS)
        lines: list[str] = []
        edges: list[str] = []
        actor = self.held(journey.fields.get("actor"), ACTOR)
        if actor is not None:
            lines.append(_node(actor))
        previous = _id(actor) if actor is not None else None
        for number, step in enumerate(steps, start=1):
            use_case = self.held(step, USE_CASE)
            label = f"{number}. {_label_of(use_case) if use_case is not None else step}"
            node = f"step_{number}"
            lines.append(f'{node}(["{_escape(label)}"])')
            if previous is not None:
                edges.append(f"{previous} --> {node}")
            previous = node
        held = (self.held(r, USE_CASE) for r in _ids(journey, RELIES_ON))
        relied_on = sorted({identity(str(u.id)): u for u in held if u}.values(), key=_order)
        if relied_on:
            lines.append('subgraph relies_on["Relied on, outside the journey"]')
            lines.extend(f"  {_node(u)}" for u in relied_on)
            lines.append("end")
        who = str(actor.id) if actor is not None else "Its actor"
        description = (
            f"The flow of {journey.id}: {who} takes {_count(len(steps), 'step')} in order"
            + (f", {', '.join(steps)}." if steps else ".")
        )
        if relied_on:
            description += (
                f" It relies on {_count(len(relied_on), 'use case')} outside the journey, "
                "drawn apart with no arrow."
            )
        return Diagram(
            id=f"journey-{journey.id}",
            title=_one_line(_label_of(journey)),
            description=_one_line(description),
            mermaid=_flowchart(_label_of(journey), description, lines, edges),
        )

    # --- the requirement map ------------------------------------------------------------

    def requirements(self, shown_as: Mapping[str, str]) -> list[Diagram]:
        requirements = self.in_force(*REQUIREMENTS)
        if not requirements:
            return []
        description = f"{_count(len(requirements), 'requirement')} in force. " + _MAP_CONVENTIONS
        lines, edges = self._map(requirements, shown_as)
        return [
            _diagram(
                REQUIREMENT_MAP,
                "The requirements and what must meet them",
                description,
                lines,
                edges,
            )
        ]

    def requirement(self, requirement: Artefact, shown_as: Mapping[str, str]) -> Diagram:
        lines, edges = self._map([requirement], shown_as)
        title = _requirement_label(requirement, shown_as)
        description = f"The map of {requirement.id}. " + _MAP_CONVENTIONS
        return _diagram(f"requirement-{requirement.id}", title, description, lines, edges)

    def _met_by(self) -> dict[str, tuple[Artefact, ...]]:
        """What meets each requirement, by its id, as `met-by` computes it (DEC-002 point
        7): one computation of it, so the map and `met-by` never disagree."""
        try:
            found = met_by.met_by(self.analysis)
        except met_by.NoAnswer as exc:
            raise NoAnswer(str(exc)) from exc
        return {identity(str(met.requirement.id)): met.by for met in found}

    def _map(
        self, requirements: Sequence[Artefact], shown_as: Mapping[str, str]
    ) -> tuple[list[str], set[str]]:
        """The nodes and edges of the map of `requirements`: each of them, what lists it,
        what it refines and its actors."""
        others: dict[str, Artefact] = {}
        edges: set[str] = set()
        meeting = self._met_by()
        for requirement in requirements:
            for lister in meeting.get(identity(str(requirement.id)), ()):
                if self.folder not in (ANYWHERE, lister.folder):
                    continue  # another analysis's, which no line of this one's draws
                others.setdefault(identity(str(lister.id)), lister)
                edges.add(f"{_id(lister)} -->|must meet| {_id(requirement)}")
            for refined in _ids(requirement, REFINES):
                target = self.held(refined, *REQUIREMENTS)
                if target is not None:
                    others.setdefault(identity(str(target.id)), target)
                    edges.add(f"{_id(requirement)} -->|refines| {_id(target)}")
            for named in _ids(requirement, ACTORS):
                actor = self.held(named, ACTOR)
                if actor is not None:
                    others.setdefault(identity(str(actor.id)), actor)
                    edges.add(f"{_id(requirement)} -->|meets a need of| {_id(actor)}")
        nodes = sorted(
            {identity(str(a.id)): a for a in (*requirements, *others.values())}.values(),
            key=_order,
        )
        return [_node(a, shown_as) for a in nodes], edges

    # --- the chain of use cases ---------------------------------------------------------

    def chain(self) -> list[Diagram]:
        """The use cases in force grouped by area, the areas in the order of their
        numbers, and an arrow from each producer each one's `after` names: dotted from a
        later area, and a solid one other solid arrows imply left out (point 5). None where
        no use case in force writes `after`."""
        use_cases = sorted(self.in_force(USE_CASE), key=_order)
        if not any(chain.writes_after(u) for u in use_cases):
            return []
        area = {_id(u): self.analysis.area(u) for u in use_cases}
        solid: set[tuple[str, str]] = set()
        dotted: set[tuple[str, str]] = set()
        for use_case in use_cases:
            for entry in chain.producers(use_case) or ():
                for named in entry:
                    if named == ENVIRONMENT:
                        solid.add((_ENVIRONMENT_NODE, _id(use_case)))
                        continue
                    producer = self.held(named, USE_CASE)
                    if producer is None:
                        continue  # not in force here: the check reports it
                    arrow = (_id(producer), _id(use_case))
                    later = chain.later(area[arrow[0]], area[arrow[1]])
                    (dotted if later else solid).add(arrow)
        dropped = chain.left_out(solid)
        edges = {f"{a} --> {b}" for a, b in solid - dropped}
        edges |= {f"{a} -.-> {b}" for a, b in dotted}
        lines: list[str] = []
        if any(a == _ENVIRONMENT_NODE for a, _b in solid):
            lines.append(f'{_ENVIRONMENT_NODE}(("The environment"))')
        lines.extend(_node(u) for u in use_cases if area[_id(u)] is None)
        for name in chain.ordered_areas([a for a in area.values() if a is not None]):
            lines.append(f'subgraph {_area_id(name)}["{_escape(name)}"]')
            lines.extend(f"  {_node(u)}" for u in use_cases if area[_id(u)] == name)
            lines.append("end")
        description = (
            f"The chain of {_count(len(use_cases), 'use case')} in force, grouped by area in "
            "the order of the areas' numbers. An arrow runs from each producer a use case "
            "names in `after` to that use case, the environment among them. A dotted arrow "
            "comes from a producer in a later area, an alternative its use case's area does "
            "not build on. "
            + (
                f"{_count(len(dropped), 'solid arrow')} that other solid arrows imply "
                f"{'is' if len(dropped) == 1 else 'are'} left out."
                if dropped
                else "No solid arrow is implied by others."
            )
        )
        return [_diagram(CHAIN, "The chain of use cases", description, lines, edges)]


#: The node of the environment in the chain, drawn beside the areas, before every one
#: (DEC-003 point 5). An artefact's node id keeps its prefix and a `_`, so none is this.
_ENVIRONMENT_NODE = "environment"


def _area_id(area: str) -> str:
    """An area's group's id: `area_` and its folder's name, each character outside letters
    and digits made `_`."""
    return "area_" + re.sub(r"[^A-Za-z0-9]", "_", area)


_MAP_CONVENTIONS = (
    "An arrow runs to each requirement from each use case or journey that must meet it, "
    "from each requirement to each requirement it refines, and from each requirement to "
    "each actor whose need it meets."
)

#: The order kinds are drawn in, so actors, requirements, use cases and journeys group.
_KIND_ORDER = (ACTOR, *REQUIREMENTS, USE_CASE, JOURNEY)


def _order(artefact: Artefact) -> tuple[int, int, str, str]:
    """By kind, then number, a number spelt otherwise as `identity` spells it, then id
    and path. The three kinds of requirement share one numbering, so they sort as one."""
    kind = REQUIREMENTS[0] if artefact.kind in REQUIREMENTS else artefact.kind
    spelt = number_in(str(artefact.id))
    number = int(spelt.split("-", 1)[1]) if spelt else 0
    return _KIND_ORDER.index(kind), number, str(artefact.id), artefact.path


def _readable(artefact: Artefact, *, chained: bool = False) -> None:
    """Raises NoAnswer unless `artefact` gives an id of its kind's shape and, in force,
    each list a diagram reads of it is a list of ids: with `chained`, a use case's
    `after` a list of lists of them too."""
    noun = REQUIREMENT if artefact.kind in REQUIREMENTS else NOUN[artefact.kind]
    if artefact.id is None or not schemas.id_pattern(artefact.kind).match(artefact.id):
        raise NoAnswer(
            f"{artefact.path} gives no {noun} id, so which {noun} it is cannot be told; "
            f"`pkit analysis validate` says why"
        )
    if artefact.withdrawn:
        return
    for field in _LISTS.get(artefact.kind, ()):
        value = artefact.fields.get(field, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise NoAnswer(
                f"{artefact.path} ({artefact.id}) gives a `{field}` that is no list of ids, "
                f"so what it relates cannot be told; `pkit analysis validate` says why"
            )
    if chained and artefact.kind == USE_CASE and chain.writes_after(artefact):
        if chain.producers(artefact) is None:
            raise NoAnswer(
                f"{artefact.path} ({artefact.id}) gives an `{AFTER}` that is no list of lists "
                f"of ids, so what follows from what cannot be told; `pkit analysis validate` "
                f"says why"
            )


def _ids(artefact: Artefact, field: str) -> list[str]:
    value = artefact.fields.get(field)
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" + ("" if number == 1 else "s")


def _node_id(artefact_id: str) -> str:
    """A node's id: the artefact's id with each character outside letters and digits made
    `_`. Ids keep their kind's prefix, so none is a word Mermaid reserves, such as `end`."""
    return re.sub(r"[^A-Za-z0-9]", "_", identity(artefact_id))


def _id(artefact: Artefact) -> str:
    return _node_id(str(artefact.id))


def _label_of(artefact: Artefact) -> str:
    """`<id> — <title>`, or `<id> — <name>` for an actor; the id alone without either."""
    name = artefact.fields.get("name" if artefact.kind == ACTOR else "title")
    return f"{artefact.id} — {name}" if isinstance(name, str) else str(artefact.id)


def _requirement_label(artefact: Artefact, shown_as: Mapping[str, str]) -> str:
    """`<id> · <kind> · <title>`, as a requirement's heading shows it."""
    title = artefact.fields.get("title")
    label = f"{artefact.id} · {shown_as.get(artefact.kind, NOUN[artefact.kind])}"
    return label + (f" · {title}" if isinstance(title, str) else "")


def _node(artefact: Artefact, shown_as: Mapping[str, str] | None = None) -> str:
    """One node: an actor a box, a use case an oval, a journey a box with bars, and a
    requirement a hexagon."""
    if artefact.kind in REQUIREMENTS:
        return f'{_id(artefact)}{{{{"{_escape(_requirement_label(artefact, shown_as or {}))}"}}}}'
    label = _escape(_label_of(artefact))
    if artefact.kind == USE_CASE:
        return f'{_id(artefact)}(["{label}"])'
    if artefact.kind == JOURNEY:
        return f'{_id(artefact)}[["{label}"]]'
    return f'{_id(artefact)}["{label}"]'


#: What Mermaid reads in a quoted label as markup, and the entity that shows it as text.
#: `#` goes first, since each entity opens with it.
_ENTITIES = (("#", "#35;"), ('"', "#quot;"), ("<", "#lt;"), (">", "#gt;"))


def _escape(text: str) -> str:
    """`text` on one line, as a quoted label shows it."""
    text = _one_line(text)
    for raw, entity in _ENTITIES:
        text = text.replace(raw, entity)
    return text


def _one_line(text: str) -> str:
    """`text` with its whitespace folded, since `accTitle` and `accDescr` end at a line's
    end, and a comment marker `%%` broken, since Mermaid would read the rest as one."""
    return " ".join(text.split()).replace("%%", "% %")


def _flowchart(title: str, description: str, nodes: Sequence[str], edges: Iterable[str]) -> str:
    lines = [
        "flowchart LR",
        f"  accTitle: {_one_line(title)}",
        f"  accDescr: {_one_line(description)}",
        *(f"  {line}" for line in nodes),
        *(f"  {edge}" for edge in edges),
    ]
    return "\n".join(lines) + "\n"


def _diagram(
    diagram_id: str, title: str, description: str, nodes: Sequence[str], edges: set[str]
) -> Diagram:
    return Diagram(
        id=diagram_id,
        title=_one_line(title),
        description=_one_line(description),
        mermaid=_flowchart(title, description, nodes, sorted(edges, key=_edge_order)),
    )


def _edge_order(edge: str) -> tuple[str, str, str]:
    """By the node an edge starts at, then the node it ends at."""
    words = edge.split()
    return words[0], words[-1], edge


def document(found: Sequence[Diagram]) -> dict[str, Any]:
    """The `--json` document: `{schema_version, diagrams}`, each diagram as `{id, title,
    description, mermaid}`."""
    return {
        "schema_version": SCHEMA_VERSION,
        "diagrams": [
            {"id": d.id, "title": d.title, "description": d.description, "mermaid": d.mermaid}
            for d in found
        ],
    }


def fenced(found: Sequence[Diagram]) -> str:
    """Each diagram in a `mermaid` fence, a blank line between two, for a page to show."""
    return "\n".join(f"```mermaid\n{d.mermaid}```\n" for d in found)
