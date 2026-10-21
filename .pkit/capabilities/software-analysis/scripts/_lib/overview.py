"""The overview of each analysis, the reader's entry point (DEC-003 point 8).

Each analysis keeps a generated overview, `overview/README.md` in its folder: a held
document in a folder of held documents of its own (COR-050 point 1), which no place
reads as an artefact. A reader on a repository host sees there, with no setup, what the
analysis holds, in the order it is built (DEC-001 point 12):

- **the concepts:** the glossary, linked, then the domain model: each view in force, in
  the order of its number, linked, by its number and its title;
- **the actors** in force, each linked, with the use cases in force it is the main actor
  of, its `actor`, and those it takes part in, its `other-actors`, each linked. After
  them, each actor of another analysis that the glossary's head lists, or that a use
  case in force names, such as `core:ACT-developer`, by that id and the name the head
  gives it, with its use cases the same way;
- **the requirements** in force, linked, then their map, where any is in force;
- **the areas** of the use cases in force, in the order of their numbers, each with its
  goal and its use cases, linked, then the chain of use cases and the use-case diagram.
  An analysis whose use cases lie in no area lists them under its use cases;
- **the journeys** in force, each linked, with its flow.

Each diagram is the query's own output, `pkit analysis diagram` (`_lib/diagrams.py`), with
its text alternative, in a section of its own, so two branches that each change what one
diagram draws conflict on that section alone.

**Front matter only.** The overview reads the front matter of the analysis it shows, and
the paths of its files, never a body (DEC-001 point 1). It reads no file of another
analysis: an actor of one is shown as this analysis's glossary's head names it.

**An area's goal** is one line kept in the capability's settings file beside the area's
folder name (`_lib/analyses.py`): what the area makes possible. It is the one text the
overview shows that no artefact holds. Where the project keeps its overview, the check
warns of an area of use cases in force without a goal. It fails a goal that names no
folder of the use cases, whatever the setting.

**Fresh by fingerprint.** The overview carries a fingerprint of what it draws: the data
it reads, never its text (`fingerprint`), with the version of what it reads (`VERSION`).
That is each artefact in force of the kinds it shows, with its id, its path and the
fields it reads, each actor of another analysis it shows with its name, and the goal of
each area it shows.
Validation compares it with the analysis in the working tree, and fails a stale
overview, naming the command. A release that only
prints the overview differently changes no fingerprint, so it fails no project. One that
reads more of the analysis raises the version, and an overview written under another one
is a warning until its command rewrites it.

**Who writes it.** Its command, `pkit analysis overview`, writes the overview of each
analysis that holds an artefact, and the stamp rewrites the overview of the analysis it
writes in (`refresh`). Each writes a file only where its bytes change, whole or not at
all. Install writes none, since install runs no command of a capability (COR-017). A
missing overview is a warning, so an upgrade fails no project.

**Keeping none.** The settings file's `overview: false` keeps no overview: the stamp
writes none, the command refuses, and the check asks for none. It warns of an overview
left in place, since nothing keeps it fresh.

**Complete, or no answer.** Where a diagram cannot be drawn in full, no overview is
written, and the check does not judge whether the one in place is fresh. The check names
what is wrong with the file.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from _lib import analyses, backbone, chain, diagrams, stamp, structure
from _lib.findings import ERROR, REPORT, WARNING, Finding
from _lib.model import (
    ACTOR,
    AFTER,
    JOURNEY,
    MUST_MEET,
    OTHER_ACTORS,
    QUALIFIER,
    RELIES_ON,
    REQUIREMENTS,
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

#: The version of what the fingerprint reads. A release that reads more of the analysis
#: raises it. An overview written under another version is a warning, never a failure,
#: until its command rewrites it, so such a release fails no project.
VERSION = 2

#: The line that carries the fingerprint and the version it reads, an HTML comment a
#: repository host does not show.
_MARK = "<!-- pkit:overview reads={reads} fingerprint={value} -->"
_MARKED = re.compile(
    r"^<!-- pkit:overview reads=(?P<reads>[0-9]+) fingerprint=(?P<value>\S+) -->$", re.M
)

#: The front-matter fields the overview reads of each kind: what it labels and links, and
#: what its diagrams draw (DEC-003 points 4 and 5).
_FIELDS: Mapping[str, tuple[str, ...]] = {
    ACTOR: ("name",),
    USE_CASE: ("title", "actor", OTHER_ACTORS, AFTER, MUST_MEET),
    JOURNEY: ("title", "actor", diagrams.STEPS, RELIES_ON, MUST_MEET),
    **dict.fromkeys(REQUIREMENTS, ("title", diagrams.REFINES, diagrams.ACTORS)),
    VIEW: ("title",),
}


@dataclass(frozen=True)
class Read:
    """What the overview of one analysis reads: the artefacts in force of the kinds it
    shows, the goal of each area it shows, `None` where the area has none, the analysis's
    folder, its glossary's path, `None` where it keeps none, and each actor of another
    analysis it shows, by its id with that analysis, such as `core:ACT-developer`, with
    the name the glossary's head gives it, `None` where the head lists it not."""

    artefacts: tuple[Artefact, ...]
    areas: Mapping[str, str | None]
    location: str
    glossary: str | None = None
    foreign: Mapping[str, str | None] = field(default_factory=dict)

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


def read(analysis: Analysis, listing: analyses.Listing, folder: str | None) -> Read:
    """What the overview of the analysis in `folder` reads: front matter and paths alone.
    Raises diagrams.NoAnswer where a diagram it shows cannot be drawn in full."""
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
    shown = _areas(analysis, [a for a in artefacts if a.kind == USE_CASE])
    return Read(
        artefacts,
        {area: goals.get(area) for area in shown},
        _top(analysis, folder),
        analyses.glossary_of(analysis, folder),
        _foreign(analysis, folder, [a for a in artefacts if a.kind == USE_CASE]),
    )


def fingerprint(analysis: Analysis, read_: Read, component: str | None) -> str:
    """The fingerprint of what the overview draws: each artefact it reads, by its kind, its
    id, its path within the analysis and the fields it reads, each actor of another
    analysis it shows, with its name, each area's goal, the glossary's path and the
    analysis's component. Never the overview's text, so a release that only prints it
    differently changes none."""
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


def render(
    analysis: Analysis,
    listing: analyses.Listing,
    folder: str | None,
    shown_as: Mapping[str, str],
) -> str:
    """The overview of the analysis in `folder`, as its command writes it. Raises
    diagrams.NoAnswer where it cannot be drawn in full."""
    read_ = read(analysis, listing, folder)
    listed = listing.of_folder(folder) if listing.several else None
    component = listed.component if listed is not None else None
    drawn = {d.id: d for d in diagrams.diagrams(analysis, None, shown_as, folder)}
    here = posixpath.dirname(path_of(analysis, folder))

    def link(artefact: Artefact) -> str:
        label = _label(artefact, shown_as).replace("[", "\\[").replace("]", "\\]")
        return f"[{label}]({posixpath.relpath(artefact.path, here)})"

    named = f"the analysis of {component}" if component else "the analysis"
    out = [
        f"# Overview of {named}",
        "",
        mark(fingerprint(analysis, read_, component)),
        "",
        f"What {named} holds, in the order it is built: its concepts, its actors, its "
        "requirements, its use cases area by area, and its journeys. The command `"
        f"{COMMAND}` writes this page from the analysis. Change the analysis, never this "
        "page (software-analysis DEC-003 point 8).",
    ]

    views = read_.of(VIEW)
    if read_.glossary or views:
        out += ["", "## Concepts", ""]
        if read_.glossary:
            out.append(
                f"The [glossary]({posixpath.relpath(read_.glossary, here)}) defines each term."
            )
        if views:
            out += [""] if read_.glossary else []
            out += ["Each view of the domain model explains a group of related concepts:", ""]
        out += [f"- {link(v)}" for v in views]

    actors = read_.of(ACTOR)
    if actors or read_.foreign:
        out += ["", "## Actors"]
        for actor in actors:
            out += ["", f"### {link(actor)}", "", *_use_cases_of(str(actor.id), read_, link)]
        for reference, name in read_.foreign.items():
            out += ["", f"### {reference}" + (f" — {name}" if name else ""), ""]
            of = f"An actor of the analysis of {qualified(reference)[0]}"
            if name is not None and read_.glossary:
                glossary = posixpath.relpath(read_.glossary, here)
                out.append(f"{of}, which the head of the [glossary]({glossary}) lists.")
            else:
                out.append(f"{of}.")
            out += ["", *_use_cases_of(reference, read_, link)]

    requirements = read_.of(*REQUIREMENTS)
    if requirements:
        out += ["", "## Requirements", ""]
        out += [f"- {link(r)}" for r in requirements]
        out += _fence(drawn.get(diagrams.REQUIREMENT_MAP))

    use_cases = read_.of(USE_CASE)
    if use_cases:
        area = {u.path: analysis.area(u) for u in use_cases}
        if read_.areas:
            out += ["", "## Areas"]
            for name, goal in read_.areas.items():
                out += ["", f"### {name}", ""]
                out.append(goal if goal else "No goal is written for this area yet.")
                out.append("")
                out += [f"- {link(u)}" for u in use_cases if area[u.path] == name]
            outside = [u for u in use_cases if area[u.path] is None]
            if outside:
                out += ["", "### Outside any area", ""]
                out += [f"- {link(u)}" for u in outside]
        else:
            out += ["", "## Use cases", ""]
            out += [f"- {link(u)}" for u in use_cases]
        chain = drawn.get(diagrams.CHAIN)
        if chain is not None:
            out += ["", "## Chain of use cases", *_fence(chain)]
        out += ["", "## Use cases and their actors", *_fence(drawn.get(diagrams.USE_CASES))]

    journeys = read_.of(JOURNEY)
    if journeys:
        out += ["", "## Journeys"]
        for journey in journeys:
            out += ["", f"### {link(journey)}", *_fence(drawn.get(f"journey-{journey.id}"))]
    return "\n".join(out) + "\n"


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


def _taking_part(use_case: Artefact) -> tuple[str | None, list[str]]:
    """The actor whose goal a use case is, its `actor`, and the other actors who take
    part, its `other-actors`, the main actor left out, each as written."""
    main = use_case.fields.get("actor")
    main = main if isinstance(main, str) else None
    others = use_case.fields.get(OTHER_ACTORS)
    listed = others if isinstance(others, list) else []
    return main, list(dict.fromkeys(o for o in listed if isinstance(o, str) and o != main))


def _use_cases_of(actor_id: str, read_: Read, link: Callable[[Artefact], str]) -> list[str]:
    """The lines under an actor's heading: the use cases in force it is the main actor
    of, then those it takes part in, each linked, or a line that says none names it."""
    use_cases = [(u, *_taking_part(u)) for u in read_.of(USE_CASE)]
    main = [f"- {link(u)}" for u, actor, _ in use_cases if actor == actor_id]
    part = [f"- {link(u)}" for u, _, others in use_cases if actor_id in others]
    if not main and not part:
        return ["No use case names it yet."]
    out = ["The use cases it is the main actor of:", "", *main] if main else []
    if part:
        out += [*([""] if out else []), "The use cases it takes part in:", "", *part]
    return out


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
        main, others = _taking_part(use_case)
        for reference in (main, *others):
            if reference is not None and qualified(reference)[0] is not None:
                named.setdefault(reference, None)
    return dict(sorted(named.items()))


def _order(artefact: Artefact) -> tuple[int, int, str, str]:
    """A view by its number, every other kind by its number, then by id and path."""
    if artefact.kind == VIEW:
        named = view_name(artefact.path)
        return 0, named[0] if named else 0, str(artefact.id), artefact.path
    spelt = number_in(str(artefact.id))
    return 1, int(spelt.split("-", 1)[1]) if spelt else 0, str(artefact.id), artefact.path


def _areas(analysis: Analysis, use_cases: Sequence[Artefact]) -> list[str]:
    """The areas `use_cases` lie in, in the order of their numbers, then by name."""
    return chain.ordered_areas([a for u in use_cases if (a := analysis.area(u)) is not None])


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
    text = render(analysis, listing, folder, shown_as)
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
    """What the check reports of the overviews and the areas' goals: for each analysis the
    project keeps, an area without a goal, a goal no area takes, and an overview missing,
    stale, or left in place where the project keeps none (DEC-003 point 8)."""
    found: list[Finding] = []
    for folder in listing.kept():
        found += _goals(analysis, listing, folder)
        found += _freshness(root, analysis, listing, folder)
    return found


def _goals(analysis: Analysis, listing: analyses.Listing, folder: str | None) -> list[Finding]:
    """An area of the use cases in force without a goal, a warning, and a goal that names
    no folder of the use cases, an error."""
    use_cases = [u for u in analysis.of_kind(USE_CASE) if u.folder == folder]
    lying = {area: u for u in use_cases if (area := analysis.area(u)) is not None}
    in_force = {area for u in use_cases if not u.withdrawn and (area := analysis.area(u))}
    goals = listing.goals(folder)
    named = listing.named(folder)
    where = (
        f"the `{analyses.AREAS}` of its entry under `{analyses.KEY}`"
        if listing.several
        else f"the `{analyses.AREAS}` at the file's top"
    ) + f" in {CONFIG}"
    found = [
        Finding(
            WARNING,
            _area_folder(analysis, lying[area], area),
            f"the area {area} of {named} has no goal: write one line beside its folder name, "
            f"in {where}, that says what the area makes possible. The overview shows it, so a "
            f"reader sees why the use cases are cut as they are (DEC-003 point 8)",
        )
        for area in sorted(in_force - goals.keys())
        if listing.keeps_overview
    ]
    found += [
        Finding(
            ERROR,
            f"{listing.goals_at(folder)}/{area}",
            f"the goal of {area} names no area of {named}: no use case lies in a folder {area} "
            f"of its use cases. A goal sits beside the folder name of an area (DEC-003 point 8) "
            f"— write the area's folder name, or remove the goal",
        )
        for area in sorted(goals.keys() - lying.keys())
    ]
    return found


def _area_folder(analysis: Analysis, use_case: Artefact, area: str) -> str:
    """The folder of `area`, one below the use cases' folder that holds `use_case`."""
    for place in (analysis.places.get(USE_CASE), analysis.nested.get(USE_CASE)):
        if place and under_place(use_case.path, place):
            depth = len(place.removesuffix("/**").split("/"))
            return "/".join([*use_case.path.split("/")[:depth], area])
    return use_case.path


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
            read(analysis, listing, folder),
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
