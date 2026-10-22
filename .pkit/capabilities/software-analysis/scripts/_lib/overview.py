"""The overview of each analysis, the reader's entry point (DEC-003 point 8).

Each analysis keeps a generated overview, `overview/README.md` in its folder: a held
document in a folder of held documents of its own (COR-050 point 1), which no place
reads as an artefact. Its reader is a newcomer first, who reads it from top to bottom, so
its order is the reader's path, in two parts: the story, read in order, and reference,
read when needed. In this order:

- **the opening:** what the component is for, the title of the accepted record the
  analysis's `purpose` names, linked. Where it names none, a line says so and names the
  command that writes one and the setting that names it, and where the record named is
  not accepted, or not held, a line says that. Then what the analysis covers, its
  component and the analyses it builds on;
- **the areas,** in the order of their numbers: each area a use case or a requirement in
  force lies in, and each the settings give a goal. Each shows its goal, what it builds
  on, its requirements and its use cases, each linked and marked where an open shortfall
  names one of its steps or variants. An area none of whose use cases writes `after`
  shows no line of what it builds on, and one that holds no use case in force reads "Not
  written yet." An analysis whose use cases lie in no area lists them under its use
  cases, which tell its story;
- **reference,** under a heading of its own, each part a section below it:
  - **who takes part:** one table, a row for each actor in force, linked, with its
    `summary` and the areas of the use cases in force it is the main actor of, its
    `actor`, or takes part in, its `other-actors`. After them, each actor of another
    analysis that the glossary's head lists, or that a use case in force names, such as
    `core:ACT-developer`, by that id and the name the head gives it;
  - **the words:** the glossary, linked, then each view in force, in the order of its
    number, by its number and its title;
  - **the requirements in no area:** those in force whose file lies in no area's folder;
  - **the journeys** in force, each linked, with its flow, the query's own output,
    `pkit analysis diagram` (`_lib/diagrams.py`), with its text alternative;
  - **not built yet,** where a use case in force lists any `shortfalls`: each entry, with
    its use case, linked, its step or variant, its record and its issue, in the use
    cases' order and then the entries' (DEC-001 point 1; `_lib/shortfalls.py`);
  - **the diagrams:** one line that names the query, as it is run for this analysis, and
    its subjects. It ends reference on every page, so every page has its heading;
- a closing line: the command writes the page, so a reader changes the analysis.

Each part lies in a section of its own, so two branches that each change what one part
shows conflict on that section alone.

**Front matter only.** The overview reads the front matter of the analysis it shows, and
the paths of its files, never a body (DEC-001 point 1). A requirement's area is the folder
of its kind's folder that holds it (`Analysis.area`). It reads no file of another
analysis: an actor of one is shown as this analysis's glossary's head names it. Beyond
the analysis, it reads only the front matter of the record its `purpose` names, where
the backbone finds it (`pkit refs lookup`).

**What an area builds on** is computed from `after` (`_lib/chain.py`): each other area
that holds a producer in force its use cases name, save one in a later area, an
alternative the area does not build on (DEC-003 point 5; DEC-001 point 12).

**An area's goal** is one line kept in the capability's settings file beside the area's
folder name (`_lib/analyses.py`): what the area makes possible. It is the one text the
overview shows that neither an artefact nor a record holds. Where the project keeps its
overview, the check warns of an area of use cases in force without a goal. A goal whose
area holds no use case shows that area as not written yet.

**What it is for.** The record `purpose` names is checked whatever the setting: the
check fails a pointer to no record, and one to a record that is not accepted. The page
shows no title of such a record, and says what is wrong with the pointer instead.

**Fresh by fingerprint.** The overview carries a fingerprint of what it draws: the data
it reads, never its text (`fingerprint`), with the version of what it reads (`VERSION`).
That is each artefact in force of the kinds it shows, with its id, its path and the
fields it reads, each actor of another analysis it shows with its name, the goal of
each area it shows, and the id, title, status and path of its purpose's record.
Validation compares it with the analysis in the working tree, and fails a stale
overview, naming the command. A release that only
prints the overview differently changes no fingerprint, so it fails no project. One that
changes what the fingerprint reads, or how it is computed, raises the version, and an
overview written under another one is a warning until its command rewrites it.

**Who writes it.** Its command, `pkit analysis overview`, writes the overview of each
analysis that holds an artefact, and the stamp rewrites the overview of the analysis it
writes in (`refresh`). Each writes a file only where its bytes change, whole or not at
all. Install writes none, since install runs no command of a capability (COR-017). A
missing overview is a warning, so an upgrade fails no project.

**Keeping none.** The settings file's `overview: false` keeps no overview: the stamp
writes none, the command refuses, and the check asks for none. It warns of an overview
left in place, since nothing keeps it fresh.

**Complete, or no answer.** Where a file of the kinds it reads cannot be read in full, as
the query would find it for any of its diagrams, or `pkit` cannot say where the purpose's
record lies, no overview is written, and the check does not judge whether the one in
place is fresh. The check names what is wrong with the file.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml.error import YAMLError

from _lib import analyses, backbone, chain, diagrams, markdown, shortfalls, stamp, structure
from _lib.findings import ERROR, REPORT, WARNING, Finding
from _lib.model import (
    ACTOR,
    AFTER,
    JOURNEY,
    OTHER_ACTORS,
    QUALIFIER,
    RELIES_ON,
    REQUIREMENTS,
    SHORTFALLS,
    USE_CASE,
    VIEW,
    Analysis,
    Artefact,
    Unreadable,
    number_in,
    qualified,
    under_place,
    view_name,
)
from _lib.numbering import CONFIG

#: The overview's folder of held documents in each analysis, and its file, which a
#: repository host shows when a reader opens the folder.
FOLDER = "overview"
FILE = "README.md"

#: The overview's command, which its findings name.
COMMAND = "pkit analysis overview"

#: The command that writes a decision record, which the opening names where the analysis
#: names no record of what its component is for.
NEW_RECORD = "pkit new decision"

#: The version of what the fingerprint reads. A release that changes what it reads, or how
#: it is computed, raises it. An overview written under another version is a warning, never a failure,
#: until its command rewrites it, so such a release fails no project.
VERSION = 4

#: The status a record's front matter gives once it decides (the acceptance gate).
ACCEPTED = "accepted"

#: The line that carries the fingerprint and the version it reads, an HTML comment a
#: repository host does not show.
_MARK = "<!-- pkit:overview reads={reads} fingerprint={value} -->"
_MARKED = re.compile(
    r"^<!-- pkit:overview reads=(?P<reads>[0-9]+) fingerprint=(?P<value>\S+) -->$", re.M
)

#: An actor's front-matter field that says who it is, the first sentence of its opening
#: (DEC-001 point 1).
SUMMARY = "summary"

#: The front-matter fields the overview reads of each kind: what it labels and links,
#: what each area builds on, who takes part and what is not built yet, and what a
#: journey's flow draws (DEC-003 points 4 and 8).
_FIELDS: Mapping[str, tuple[str, ...]] = {
    ACTOR: ("name", SUMMARY),
    USE_CASE: ("title", "actor", OTHER_ACTORS, AFTER, SHORTFALLS),
    JOURNEY: ("title", "actor", diagrams.STEPS, RELIES_ON),
    **dict.fromkeys(REQUIREMENTS, ("title",)),
    VIEW: ("title",),
}

#: The query the page names, which prints the analysis's diagrams (DEC-003 point 7).
DIAGRAM_COMMAND = "pkit analysis diagram"

#: The headings the page's own links point at, as a repository host makes their anchors,
#: and the heading of reference, the page's second part.
_USE_CASES, _OUTSIDE, _NOT_BUILT = "Use cases", "Outside any area", "Not built yet"
_REFERENCE, _DIAGRAMS = "Reference", "Diagrams"


@dataclass(frozen=True)
class Record:
    """A decision record as the overview and its check read it: its file,
    repository-relative, and the title and the status its front matter gives, empty
    where it gives none."""

    path: str
    title: str
    status: str


@dataclass(frozen=True)
class Purpose:
    """The record an analysis names as what its component is for: its id as the settings
    give it, and, where the repository holds it, its file, repository-relative, and the
    title and the status its front matter gives; `path` is `None` where it holds none."""

    record: str
    path: str | None = None
    title: str = ""
    status: str = ""

    @property
    def accepted(self) -> bool:
        return self.path is not None and self.status == ACCEPTED


@dataclass(frozen=True)
class Read:
    """What the overview of one analysis reads: the artefacts in force of the kinds it
    shows, each area it shows with its goal, `None` where the area has none, the
    analysis's folder, its glossary's path, `None` where it keeps none, each actor of
    another analysis it shows, by its id with that analysis, such as
    `core:ACT-developer`, with the name the glossary's head gives it, `None` where the
    head lists it not, and the record its purpose names, `None` where it names none."""

    artefacts: tuple[Artefact, ...]
    areas: Mapping[str, str | None]
    location: str
    glossary: str | None = None
    foreign: Mapping[str, str | None] = field(default_factory=dict)
    purpose: Purpose | None = None

    def of(self, *kinds: str) -> list[Artefact]:
        return [a for a in self.artefacts if a.kind in kinds]


def path_of(analysis: Analysis, folder: str | None) -> str:
    """The overview's path in the repository: `overview/README.md` in the folder of the
    analysis in `folder`, `None` the location's top."""
    return posixpath.join(_top(analysis, folder), FOLDER, FILE)


def _top(analysis: Analysis, folder: str | None) -> str:
    """The folder of the analysis in `folder` of the location, `None` its top."""
    location = posixpath.normpath(analysis.location or ".")
    return location if folder is None else posixpath.join(location, folder)


def read(
    analysis: Analysis, listing: analyses.Listing, folder: str | None, root: Path | None = None
) -> Read:
    """What the overview of the analysis in `folder` reads: front matter and paths alone,
    and the front matter of its purpose's record, found from the repository at `root`.
    Raises diagrams.NoAnswer where a file of the kinds it reads cannot be read in full, as
    the query would find it for any of its diagrams, or where whether the repository
    holds the purpose's record cannot be read."""
    diagrams.diagrams(analysis, None, {}, folder)
    artefacts = tuple(
        sorted(
            (
                a
                for a in analysis.artefacts
                if a.folder == folder and a.kind in _FIELDS and not a.withdrawn
            ),
            key=_order,
        )
    )
    goals = listing.goals(folder)
    lying = [a for a in artefacts if a.kind == USE_CASE or a.kind in REQUIREMENTS]
    shown = chain.ordered_areas(
        [*goals, *(area for a in lying if (area := analysis.area(a)) is not None)]
    )
    named = listing.purpose_of(folder)
    return Read(
        artefacts,
        {area: goals.get(area) for area in shown},
        _top(analysis, folder),
        analyses.glossary_of(analysis, folder),
        _foreign(analysis, folder, [a for a in artefacts if a.kind == USE_CASE]),
        _purpose(root, named) if named is not None else None,
    )


def record(root: Path, record_id: str) -> Record | None:
    """The decision record `record_id` names, as `pkit refs lookup` finds it: its file and
    what its front matter gives; `None` where it names no record the repository holds, or
    one whose file cannot be read. Raises Unreadable where `pkit` cannot be run."""
    rel = backbone.record_file(root, record_id)
    if rel is None:
        return None
    try:
        text = (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    yaml_text = markdown.split(text)[0]
    try:
        front = markdown.load(yaml_text) if yaml_text is not None else None
    except YAMLError:
        front = None
    front = front if isinstance(front, Mapping) else {}
    title, status = front.get("title"), front.get("status")
    return Record(
        rel,
        " ".join(title.split()) if isinstance(title, str) else "",
        status if isinstance(status, str) else "",
    )


def _purpose(root: Path | None, record_id: str) -> Purpose:
    """The record the analysis names as what its component is for, as the repository
    holds it, or not. A record that is not accepted, or none, is said on the page, and
    its check fails the pointer (`_purpose_findings`). Raises diagrams.NoAnswer where
    whether the repository holds it cannot be read."""
    said = f"its purpose, `{analyses.PURPOSE}: {record_id}` in {CONFIG}"
    if root is None:
        raise diagrams.NoAnswer(f"{said}, is not read here")
    try:
        found = record(root, record_id)
    except Unreadable as exc:
        raise diagrams.NoAnswer(f"{said}, cannot be read: {exc}") from exc
    if found is None:
        return Purpose(record_id)
    return Purpose(record_id, found.path, found.title, found.status)


def fingerprint(analysis: Analysis, read_: Read, component: str | None) -> str:
    """The fingerprint of what the overview draws: each artefact it reads, by its kind, its
    id, its path within the analysis and the fields it reads, each actor of another
    analysis it shows, with its name, each area's goal, the glossary's path, the
    analysis's component, and its purpose's record, by its id, its title and its path.
    Never the overview's text, so a release that only prints it differently changes
    none."""
    purpose = read_.purpose
    data = {
        "version": VERSION,
        "component": component,
        "artefacts": [
            {
                "kind": a.kind,
                "id": a.id,
                "path": posixpath.relpath(a.path, read_.location),
                "fields": {f: a.fields[f] for f in _FIELDS[a.kind] if f in a.fields},
                **({"area": analysis.area(a)} if a.kind == USE_CASE else {}),
            }
            for a in read_.artefacts
        ],
        "foreign": dict(read_.foreign),
        "areas": dict(read_.areas),
        "glossary": (posixpath.relpath(read_.glossary, read_.location) if read_.glossary else None),
        "purpose": (
            {
                "record": purpose.record,
                "title": purpose.title,
                "status": purpose.status,
                "path": (
                    posixpath.relpath(purpose.path, read_.location)
                    if purpose.path is not None
                    else None
                ),
            }
            if purpose is not None
            else None
        ),
    }
    text = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def mark(value: str) -> str:
    """The line that carries the fingerprint `value`, under this release's version."""
    return _MARK.format(reads=VERSION, value=value)


def written_fingerprint(text: str) -> tuple[int, str] | None:
    """The version and the fingerprint an overview's text carries; `None` where it
    carries none."""
    found = _MARKED.search(text)
    return (int(found["reads"]), found["value"]) if found else None


# --- the page ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Page:
    """What the page's parts share: the analysis and what its overview reads, the folder
    the page lies in, each use case's area, and each analysis's name in its words."""

    analysis: Analysis
    read: Read
    here: str
    shown_as: Mapping[str, str]
    area: Mapping[str, str | None]

    def link(self, artefact: Artefact) -> str:
        label = _label(artefact, self.shown_as).replace("[", "\\[").replace("]", "\\]")
        return f"[{label}]({posixpath.relpath(artefact.path, self.here)})"

    def to(self, path: str) -> str:
        return posixpath.relpath(path, self.here)


def render(
    analysis: Analysis,
    listing: analyses.Listing,
    folder: str | None,
    shown_as: Mapping[str, str],
    root: Path | None = None,
) -> str:
    """The overview of the analysis in `folder`, as its command writes it, its purpose's
    record found from the repository at `root`. Raises diagrams.NoAnswer where it cannot
    be drawn in full."""
    read_ = read(analysis, listing, folder, root)
    listed = listing.of_folder(folder) if listing.several else None
    component = listed.component if listed is not None else None
    flows = {d.id: d for d in diagrams.diagrams(analysis, diagrams.JOURNEYS, shown_as, folder)}
    use_cases = read_.of(USE_CASE)
    page = _Page(
        analysis,
        read_,
        posixpath.dirname(path_of(analysis, folder)),
        shown_as,
        {u.path: analysis.area(u) for u in use_cases},
    )

    named = f"the analysis of {component}" if component else "the analysis"
    out = [f"# Overview of {named}", "", mark(fingerprint(analysis, read_, component))]
    out += _opening(page, listing, folder, listed)
    out += _areas_part(page)
    out += ["", f"## {_REFERENCE}", *_reference(page, flows, component)]
    out += [
        "",
        "---",
        "",
        f"The command `{COMMAND}` writes this page from the analysis. Change the analysis, "
        "never this page (software-analysis DEC-003 point 8).",
    ]
    return "\n".join(out) + "\n"


def _opening(
    page: _Page, listing: analyses.Listing, folder: str | None, listed: analyses.Listed | None
) -> list[str]:
    """What the component is for, and what the analysis covers."""
    read_ = page.read
    subject = listed.component if listed is not None else "the system"
    out = [""]
    purpose = read_.purpose
    if purpose is not None and purpose.accepted and purpose.path is not None:
        title = (purpose.title or purpose.record).replace("[", "\\[").replace("]", "\\]")
        end = "" if title.endswith((".", "?", "!")) else "."
        out.append(f"[{title}]({page.to(purpose.path)}){end}")
    elif purpose is not None:
        status = purpose.status or "of no status"
        held = (
            f"it is {status}, not accepted"
            if purpose.path is not None
            else "the repository holds no record of that id"
        )
        out.append(
            f"`{purpose.record}` is named as the record of what {subject} is for, and {held}. "
            f"Only an accepted record states it (software-analysis DEC-003 point 8)."
        )
    else:
        where = (
            f"in the entry of {listed.component} under `{analyses.KEY}` in `{CONFIG}`"
            if listed is not None
            else f"at the top of `{CONFIG}`"
        )
        out.append(
            f"No record states what {subject} is for yet. Write one with `{NEW_RECORD}`, and "
            f"name it as `{analyses.PURPOSE}` {where}."
        )
    return [*out, "", _covers(listed)]


def _covers(listed: analyses.Listed | None) -> str:
    """What the analysis covers: its component, and the analyses it builds on."""
    if listed is None:
        return "This analysis covers the system as one component, and builds on no other analysis."
    built = [b.analysis + (" (optional)" if b.optional else "") for b in listed.builds_on]
    if not built:
        on = "no other analysis"
    elif len(built) == 1:
        on = f"the analysis of {built[0]}"
    else:
        on = f"the analyses of {', '.join(built[:-1])} and {built[-1]}"
    return f"This analysis covers {listed.component}, and builds on {on}."


def _areas_part(page: _Page) -> list[str]:
    """The areas in the order of their numbers, each with its goal, what it builds on,
    its requirements and its use cases, then the use cases outside any area; or, where no
    area is shown, the use cases."""
    read_ = page.read
    use_cases = read_.of(USE_CASE)
    if not read_.areas:
        if not use_cases:
            return []
        return ["", f"## {_USE_CASES}", "", *(_use_case_line(page, u) for u in use_cases)]
    out = ["", "## Areas"]
    requirements = read_.of(*REQUIREMENTS)
    for name, goal in read_.areas.items():
        out += ["", f"### {name}", ""]
        out.append(goal if goal else "No goal is written for this area yet.")
        own = [u for u in use_cases if page.area[u.path] == name]
        bound = [r for r in requirements if page.analysis.area(r) == name]
        if any(chain.writes_after(u) for u in own):
            built = _builds_on(page, own, name)
            out += ["", f"**Builds on:** {_joined(built) if built else 'no other area'}."]
        if bound or own:
            out += ["", "**Its requirements:**" + ("" if bound else " none.")]
            out += ["", *(f"- {page.link(r)}" for r in bound)] if bound else []
        if own:
            out += ["", "**Its use cases:**", "", *(_use_case_line(page, u) for u in own)]
        else:
            out += ["", "Not written yet."]
    outside = [u for u in use_cases if page.area[u.path] is None]
    if outside:
        out += ["", f"### {_OUTSIDE}", "", *(_use_case_line(page, u) for u in outside)]
    return out


def _use_case_line(page: _Page, use_case: Artefact) -> str:
    """A use case's item: its link, marked where an open shortfall names one of its steps
    or variants."""
    places = list(dict.fromkeys(e.place for e in shortfalls.entries(use_case) or ()))
    if not places:
        return f"- {page.link(use_case)}"
    return f"- {page.link(use_case)} ([not built yet](#{_anchor(_NOT_BUILT)}): {', '.join(places)})"


def _builds_on(page: _Page, own: Sequence[Artefact], area: str) -> list[str]:
    """The other areas that hold a producer in force the use cases of `area` name in
    `after`, in the order of their numbers, save one in a later area (DEC-003 point 5).
    The environment is no area."""
    in_force = {str(u.id): u for u in page.read.of(USE_CASE)}
    found: list[str] = []
    for use_case in own:
        for entry in chain.producers(use_case) or ():
            for named in entry:
                producer = in_force.get(named)
                theirs = page.area.get(producer.path) if producer is not None else None
                if theirs is None or theirs == area or chain.later(theirs, area):
                    continue
                found.append(theirs)
    return chain.ordered_areas(found)


def _joined(areas: Sequence[str]) -> str:
    """Areas as links to their headings, joined as a sentence lists them."""
    links = [f"[{a}](#{_anchor(a)})" for a in areas]
    return links[0] if len(links) == 1 else f"{', '.join(links[:-1])} and {links[-1]}"


def _reference(
    page: _Page, flows: Mapping[str, diagrams.Diagram], component: str | None
) -> list[str]:
    """Reference, read when needed, each part a section below its heading: who takes part,
    the concepts, the requirements in no area, the journeys, each with its flow, and what
    is not built yet, each where the analysis holds it. Then, on every page, the line that
    names the query of the diagrams, as it is run for the analysis of `component`, `None`
    the one analysis the project keeps where it lists none."""
    read_ = page.read
    out = _taking_part(page)

    views = read_.of(VIEW)
    if read_.glossary or views:
        out += ["", "### Concepts", ""]
        if read_.glossary:
            out.append(f"The [glossary]({page.to(read_.glossary)}) defines each term.")
        if views:
            out += [""] if read_.glossary else []
            out += ["Each view of the domain model explains a group of related concepts:", ""]
        out += [f"- {page.link(v)}" for v in views]

    every = [r for r in read_.of(*REQUIREMENTS) if page.analysis.area(r) is None]
    if every:
        heading = "Requirements in no area" if read_.areas else "Requirements"
        out += ["", f"### {heading}", "", *(f"- {page.link(r)}" for r in every)]

    journeys = read_.of(JOURNEY)
    if journeys:
        out += ["", "### Journeys"]
        for journey in journeys:
            out += ["", f"#### {page.link(journey)}", *_fence(flows.get(f"journey-{journey.id}"))]

    open_ = [(u, entry) for u in read_.of(USE_CASE) for entry in shortfalls.entries(u) or ()]
    if open_:
        out += [
            "",
            f"### {_NOT_BUILT}",
            "",
            "What the use cases describe and the system does not do yet, each with the record "
            "that decides it and the issue that tracks it (software-analysis DEC-001 point 1):",
            "",
        ]
        out += [
            f"- {page.link(u)}: {entry.place}, decided by `{entry.record}`, tracked in "
            f"{_issue(entry.issue)}"
            for u, entry in open_
        ]

    return [*out, "", f"### {_DIAGRAMS}", "", _diagrams_line(component)]


def _diagrams_line(component: str | None) -> str:
    """The line that names the query of the analysis's diagrams, as it is run for the
    analysis of `component`, and its subjects (DEC-003 points 7 and 8)."""
    command = DIAGRAM_COMMAND + (f" --analysis {component}" if component else "")
    named = [f"`{s}`" for s in diagrams.SUBJECTS]
    return (
        f"`{command}` prints this analysis's diagrams from the working tree. Its subjects "
        f"are {', '.join(named[:-1])} and {named[-1]}, or a journey's or a requirement's id."
    )


def _taking_part(page: _Page) -> list[str]:
    """One table of who takes part: each actor in force, linked, who it is and the areas it
    acts in, then each actor of another analysis, as the glossary's head names it."""
    read_ = page.read
    actors = read_.of(ACTOR)
    if not actors and not read_.foreign:
        return []
    rows = [(page.link(a), _cell(a.fields.get(SUMMARY)), _acts_in(page, str(a.id))) for a in actors]
    for reference, name in read_.foreign.items():
        of = f"An actor of the analysis of {qualified(reference)[0]}"
        if name is not None and read_.glossary:
            who = f"{of}, which the head of the [glossary]({page.to(read_.glossary)}) lists."
        else:
            who = f"{of}."
        shown = f"{reference} — {_cell(name)}" if name else reference
        rows.append((shown, who, _acts_in(page, reference)))
    return [
        "",
        "### Who takes part",
        "",
        "| Actor | Who they are | Areas they act in |",
        "| --- | --- | --- |",
        *(f"| {actor} | {who} | {areas} |" for actor, who, areas in rows),
    ]


def _cell(text: object) -> str:
    """A text as a table's cell shows it: on one line, a `|` escaped; empty where there is
    none."""
    if not isinstance(text, str):
        return ""
    return " ".join(text.split()).replace("|", "\\|")


def _acts_in(page: _Page, actor_id: str) -> str:
    """The areas of the use cases in force `actor_id` is the main actor of or takes part
    in, linked, in the order of their numbers; then the use cases outside any area."""
    acting = [u for u in page.read.of(USE_CASE) if actor_id in _actors_of(u)]
    if not acting:
        return "No use case names it yet."
    areas = chain.ordered_areas([a for u in acting if (a := page.area[u.path]) is not None])
    shown = [f"[{a}](#{_anchor(a)})" for a in areas]
    if any(page.area[u.path] is None for u in acting):
        shown.append(
            f"[outside any area](#{_anchor(_OUTSIDE)})"
            if page.read.areas
            else f"[the use cases](#{_anchor(_USE_CASES)})"
        )
    return ", ".join(shown)


def _anchor(heading: str) -> str:
    """A heading's anchor as a repository host makes it: lower case, each space a hyphen,
    and every character but letters, digits, hyphens and underscores dropped."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def _issue(issue: str) -> str:
    """An issue as the overview shows it: a link as itself, any other in a code span."""
    if issue.startswith(("https://", "http://")):
        return f"<{issue}>"
    ticks = "``" if "`" in issue else "`"
    return f"{ticks}{issue}{ticks}"


def _fence(diagram: diagrams.Diagram | None) -> list[str]:
    """A diagram in its `mermaid` fence, a blank line before it."""
    if diagram is None:
        return []
    return ["", "```mermaid", *diagram.mermaid.rstrip("\n").split("\n"), "```"]


def _label(artefact: Artefact, shown_as: Mapping[str, str]) -> str:
    """`<id> — <title>`, an actor's name in its place and a view's number, as its file's
    name spells it, in its id's, and `<id> · <kind> · <title>` for a requirement, as its
    heading shows it."""
    if artefact.kind in REQUIREMENTS:
        title = artefact.fields.get("title")
        shown = shown_as.get(artefact.kind, artefact.kind)
        return f"{artefact.id} · {shown}" + (f" · {title}" if isinstance(title, str) else "")
    name = artefact.fields.get("name" if artefact.kind == ACTOR else "title")
    first = _number(artefact) if artefact.kind == VIEW else None
    first = first or str(artefact.id)
    return f"{first} — {name}" if isinstance(name, str) else first


def _number(view: Artefact) -> str | None:
    """A view's number as its file's name spells it, `010` for `…/010-orders.md`; `None`
    for a name that opens with no number (DEC-004 point 4)."""
    if view_name(view.path) is None:
        return None
    return view.path.rsplit("/", 1)[-1].split("-", 1)[0]


def _actors_of(use_case: Artefact) -> tuple[str, ...]:
    """The actors who take part in a use case: its `actor`, then its `other-actors`, each
    as written, once."""
    main = use_case.fields.get("actor")
    others = use_case.fields.get(OTHER_ACTORS)
    listed = [main, *(others if isinstance(others, list) else [])]
    return tuple(dict.fromkeys(a for a in listed if isinstance(a, str)))


def _foreign(
    analysis: Analysis, folder: str | None, use_cases: Sequence[Artefact]
) -> dict[str, str | None]:
    """Each actor of another analysis the overview shows, by its id with that analysis, in
    the order of that id: each the glossary's head lists, with the name it gives, and each
    a use case in force names, `None` where the head lists it not (DEC-001 point 2)."""
    head = analyses.head(analysis, folder)
    named: dict[str, str | None] = {}
    for taken in head.taken if head is not None else ():
        for actor in taken.actors:
            named.setdefault(f"{taken.analysis}{QUALIFIER}{actor.id}", actor.name)
    for use_case in use_cases:
        for reference in _actors_of(use_case):
            if qualified(reference)[0] is not None:
                named.setdefault(reference, None)
    return dict(sorted(named.items()))


def _order(artefact: Artefact) -> tuple[int, int, str, str]:
    """A view by its number, every other kind by its number, then by id and path."""
    if artefact.kind == VIEW:
        named = view_name(artefact.path)
        return 0, named[0] if named else 0, str(artefact.id), artefact.path
    spelt = number_in(str(artefact.id))
    return 1, int(spelt.split("-", 1)[1]) if spelt else 0, str(artefact.id), artefact.path


# --- writing it --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Written:
    """An overview the command or the stamp wrote, or found fresh: its path, and whether
    its bytes changed."""

    path: str
    changed: bool


def write(
    root: Path,
    analysis: Analysis,
    listing: analyses.Listing,
    folder: str | None,
    shown_as: Mapping[str, str],
    *,
    record: stamp.Recorder | None = None,
) -> Written:
    """Write the overview of the analysis in `folder` where its bytes change, whole or not
    at all, recording the analysis location through `record` where it is not recorded yet
    (COR-049 point 5). Raises diagrams.NoAnswer where it cannot be drawn in full, and
    stamp.Refused where it cannot be written."""
    text = render(analysis, listing, folder, shown_as, root)
    rel = path_of(analysis, folder)
    target = root / rel
    if target.is_file() and target.read_bytes() == text.encode("utf-8"):
        return Written(rel, False)
    if record is None:
        stamp.refuse_links(root, target, rel)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            stamp.write_whole(target, text.encode("utf-8"))
        except OSError as exc:
            raise stamp.Refused(f"{rel} could not be written: {exc}") from exc
    else:
        stamp.write_and_record(root, target, rel, text, record)
    return Written(rel, True)


def shown_as() -> dict[str, str]:
    """Each kind of requirement as its heading shows it, as the shipped structures give it."""
    kinds = structure.read_kinds()
    return {kind: kinds[kind].shown_as or kind for kind in REQUIREMENTS if kind in kinds}


def refresh(root: Path, named: str | None) -> tuple[str | None, str | None]:
    """The stamp's refresh of the overview of the analysis it wrote in, `named` by its
    component as `--analysis` names it: a note where it wrote the overview, and a warning
    where it could not. Nothing where the project keeps no overview."""
    listing = analyses.read(root)
    if not listing.keeps_overview:
        return None, None
    try:
        folder = analyses.folder_named(listing, named, "to write in")
        analysis = backbone.read_analysis(root)
        written = write(root, analysis, listing, folder, shown_as())
    except (
        analyses.Unnamed,
        Unreadable,
        diagrams.NoAnswer,
        stamp.Refused,
        structure.Unreadable,
    ) as exc:
        return None, (
            f"the overview was not rewritten: {exc}. Once that is mended, run `{COMMAND}` "
            f"(DEC-003 point 8)"
        )
    if not written.changed:
        return None, None
    return f"wrote the overview, {written.path} (DEC-003 point 8)", None


# --- what the check holds ----------------------------------------------------------------------


def findings(root: Path, analysis: Analysis, listing: analyses.Listing) -> list[Finding]:
    """What the check reports of the overviews, the areas' goals and the purposes: for
    each analysis the project keeps, an area without a goal, a purpose that names no
    accepted record, and an overview missing, stale, or left in place where the project
    keeps none (DEC-003 point 8)."""
    found: list[Finding] = []
    for folder in listing.kept():
        found += _goals(analysis, listing, folder)
        found += _purpose_findings(root, listing, folder)
        found += _freshness(root, analysis, listing, folder)
    return found


def _goals(analysis: Analysis, listing: analyses.Listing, folder: str | None) -> list[Finding]:
    """An area of the use cases or the requirements in force without a goal, a warning,
    where the project keeps its overview. A goal whose area holds no use case shows that
    area as not written yet, so no goal fails."""
    if not listing.keeps_overview:
        return []
    lying = {
        area: a
        for a in analysis.artefacts
        if a.folder == folder
        and (a.kind == USE_CASE or a.kind in REQUIREMENTS)
        and not a.withdrawn
        and (area := analysis.area(a)) is not None
    }
    in_force = set(lying)
    named = listing.named(folder)
    where = (
        f"the `{analyses.AREAS}` of its entry under `{analyses.KEY}`"
        if listing.several
        else f"the `{analyses.AREAS}` at the file's top"
    ) + f" in {CONFIG}"
    return [
        Finding(
            WARNING,
            _area_folder(analysis, lying[area], area),
            f"the area {area} of {named} has no goal: write one line beside its folder name, "
            f"in {where}, that says what the area makes possible. The overview shows it, so a "
            f"reader sees why the use cases are cut as they are (DEC-003 point 8)",
        )
        for area in sorted(in_force - listing.goals(folder).keys())
    ]


def _purpose_findings(root: Path, listing: analyses.Listing, folder: str | None) -> list[Finding]:
    """A purpose that names no record the repository holds, or a record that is not
    accepted, an error, whatever the setting `overview` (DEC-003 point 8)."""
    named = listing.purpose_of(folder)
    if named is None:
        return []
    where = listing.purpose_at(folder)
    listed = listing.of_folder(folder)
    capability = named.partition(":")[0] if ":" in named else None
    if listed is not None and capability is not None and capability != listed.component:
        return [
            Finding(
                ERROR,
                where,
                f"{named} is a decision of {capability}, and the component of "
                f"{listing.named(folder)} is {listed.component}: `{analyses.PURPOSE}` names a "
                f"record the project owns, a project or an architecture record, or a decision "
                f"of the analysis's own component (DEC-003 point 8)",
            )
        ]
    try:
        found = record(root, named)
    except Unreadable as exc:
        return [
            Finding(ERROR, where, f"whether {named} is an accepted record cannot be read: {exc}")
        ]
    if found is None:
        return [
            Finding(
                ERROR,
                where,
                f"`{named}` names no record the repository holds: `{analyses.PURPOSE}` names "
                f"the accepted decision record that states what the component of "
                f"{listing.named(folder)} is for (DEC-003 point 8). Name one, or remove the "
                f"setting",
            )
        ]
    if found.status != ACCEPTED:
        return [
            Finding(
                ERROR,
                where,
                f"{named} is {found.status or 'of no status'}, not accepted: only an accepted "
                f"record states what a component is for, as the acceptance gate asks. Accept "
                f"it, or name an accepted one (DEC-003 point 8)",
            )
        ]
    return []


def _area_folder(analysis: Analysis, artefact: Artefact, area: str) -> str:
    """The folder of `area`, one below the folder of the place of its kind that holds
    `artefact`: a use case, or a requirement."""
    for place in (analysis.places.get(artefact.kind), analysis.nested.get(artefact.kind)):
        if place and under_place(artefact.path, place):
            depth = len(place.removesuffix("/**").split("/"))
            return "/".join([*artefact.path.split("/")[:depth], area])
    return artefact.path


def _freshness(
    root: Path, analysis: Analysis, listing: analyses.Listing, folder: str | None
) -> list[Finding]:
    rel = path_of(analysis, folder)
    target = root / rel
    named = listing.named(folder)
    if not listing.keeps_overview:
        if not target.is_file():
            return []
        return [
            Finding(
                WARNING,
                rel,
                f"the setting `{analyses.OVERVIEW}: false` in {CONFIG} keeps no overview, so "
                f"nothing keeps this one fresh: delete it, or remove the setting and run "
                f"`{COMMAND}` (DEC-003 point 8)",
            )
        ]
    if not target.is_file():
        if not any(a.folder == folder for a in analysis.artefacts):
            return []
        return [
            Finding(
                WARNING,
                rel,
                f"{named} has no overview, the reader's entry point: run `{COMMAND}` to write "
                f"it, or keep none with `{analyses.OVERVIEW}: false` in {CONFIG} (DEC-003 "
                f"point 8)",
            )
        ]
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [Finding(ERROR, rel, f"it cannot be read ({exc}): run `{COMMAND}` to write it anew")]
    written = written_fingerprint(text)
    if written is None:
        return [
            Finding(
                ERROR,
                rel,
                f"it carries no fingerprint of what it draws, the line its command writes, "
                f"`{_MARK.format(reads='…', value='…')}`, so whether it is fresh cannot be "
                f"told: run `{COMMAND}` to write it anew (DEC-003 point 8)",
            )
        ]
    listed = listing.of_folder(folder) if listing.several else None
    try:
        now = fingerprint(
            analysis,
            read(analysis, listing, folder, root),
            listed.component if listed is not None else None,
        )
    except diagrams.NoAnswer as exc:
        return [
            Finding(
                REPORT,
                rel,
                f"whether it is fresh is not checked, since what it draws cannot be read in "
                f"full: {exc}",
            )
        ]
    reads, value = written
    if value == now:
        return []
    if reads != VERSION:
        return [
            Finding(
                WARNING,
                rel,
                f"it was written by a release that reads other data of the analysis "
                f"(reads={reads}, and this release reads {VERSION}), so whether it is fresh "
                f"cannot be told: run `{COMMAND}` to write it anew. It fails nothing until "
                f"then (DEC-003 point 8)",
            )
        ]
    return [
        Finding(
            ERROR,
            rel,
            f"it is stale: what it draws changed since it was written, such as a title, a "
            f"relation, a status, an actor of a use case or an area's goal. Run `{COMMAND}` "
            f"to write it anew, and commit it with the change (DEC-003 point 8)",
        )
    ]
