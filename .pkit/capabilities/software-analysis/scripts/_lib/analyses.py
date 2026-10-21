"""The analyses a repository keeps, one for each component that keeps one (DEC-001 point 2).

A project with one analysis keeps it at the top of the analysis location, and lists
nothing. A project that keeps several lists them in the capability's settings file,
`project/config.yaml`, as `analyses`: each with its component, the folder of the
location it lies in, named after the component, and the analyses it builds on, each
by its component's name and whether it is optional. The places match both layouts
(`model.NESTED_PLACES`), so which analysis holds an artefact is the folder it lies in:

- **no list:** the one analysis at the location's top holds every artefact there, and
  an artefact in a folder below lies in no analysis;
- **a list:** each listed analysis holds the artefacts in its folder, and an artefact
  at the location's top, or in a folder no entry lists, lies in no analysis.

**What an analysis builds on.** Its glossary's head lists what it takes from each
analysis it builds on: the version its links name, the terms and the actors, each by
id and name, and the needs each actor brings to it. That is data in the glossary's
front matter, `builds-on`, a list, so the backbone never reads it as an entry of the
collection, and the check holds the head's text to it (`forms.BUILDS_ON_MATCH`). An
actor of another analysis is named with that analysis, `core:ACT-developer`, and
resolves against the actors the head lists from it.

**Areas' goals.** Each analysis may give each area of its use cases a goal: one line,
kept as data beside the area's folder name, that says what the area makes possible
(DEC-003 point 8). A listed analysis keeps them in its entry's `areas`, and the one
analysis at the location's top in the file's own `areas`. The overview shows each beside
its area (`_lib/overview.py`).

**The overview.** The file's `overview` keeps the overview of each analysis, or, set to
`false`, keeps none (DEC-003 point 8). Left out, it keeps one.

**Dependencies.** Where a component declares what it depends on, as a capability does
in its package metadata (COR-030), the configuration's list is held to it: the
backbone is the analysis whose component is `core`, required, and each capability it
requires names its own, optional where it is. Each floor it declares is the version a
head's links to that analysis are compared with. Elsewhere, the list is the
project's own statement of them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import markdown, schemas
from _lib.findings import ERROR, Finding, at
from _lib.model import ACTOR, NOUN, TERM, Analysis, qualified
from _lib.numbering import CONFIG

#: The key of the capability's settings file that lists the analyses.
KEY = "analyses"

#: The key that gives each area of an analysis's use cases its goal: in a listed
#: analysis's entry, and at the file's top for the one analysis at the location's top.
AREAS = "areas"

#: The key that keeps the overview of each analysis, or, `false`, keeps none (DEC-003
#: point 8).
OVERVIEW = "overview"

#: An area's folder name: a word, as a slug is, after an optional number and a hyphen,
#: such as `010-develop` (DEC-001 point 2).
_AREA = re.compile(r"^(?:[0-9]+-)?[a-z][a-z0-9-]*$")

#: The key of a glossary's front matter that holds what its analysis takes from the
#: analyses it builds on: a list, so the backbone never reads it as an entry.
HEAD = "builds-on"

#: The component whose analysis is the backbone's: what a capability's
#: `requires_backbone` depends on, and whose floor a head's links are compared with.
BACKBONE = "core"

#: Where a capability's package metadata lies, by its name.
PACKAGE = ".pkit/capabilities/{name}/package.yaml"

_FLOOR = re.compile(r"^\s*>=\s*(?P<version>\S+?)\s*$")


@dataclass(frozen=True)
class BuildsOn:
    """An analysis a listed one builds on: its component's name, whether it is
    optional, and its index in the entry's list."""

    analysis: str
    optional: bool
    index: int


@dataclass(frozen=True)
class Listed:
    """One analysis the settings file lists: its index, its component, its folder and
    what it builds on."""

    index: int
    component: str
    folder: str
    builds_on: tuple[BuildsOn, ...]
    areas: tuple[tuple[str, str], ...] = ()

    @property
    def where(self) -> str:
        return at(CONFIG, f"/{KEY}/{self.index}")

    def builds_on_at(self, entry: BuildsOn) -> str:
        return at(CONFIG, f"/{KEY}/{self.index}/{HEAD}/{entry.index}")

    def built_on(self, component: str) -> BuildsOn | None:
        return next((b for b in self.builds_on if b.analysis == component), None)


@dataclass(frozen=True)
class Listing:
    """The analyses the settings file lists, each of the shape its companion asks; none
    where it lists none, so one analysis lies at the location's top. `problems` are
    what the list breaks beyond its shape: a component or a folder listed twice, or an
    analysis that builds on itself or names one twice. Its shape is the companion's
    to report, through `pkit validate`'s check of the project's data."""

    analyses: tuple[Listed, ...] = ()
    problems: tuple[Finding, ...] = ()
    areas: tuple[tuple[str, str], ...] = ()
    keeps_overview: bool = True

    @property
    def several(self) -> bool:
        """Whether the project lists its analyses, each in its component's folder."""
        return bool(self.analyses)

    def of_folder(self, folder: str | None) -> Listed | None:
        return next((a for a in self.analyses if a.folder == folder), None)

    def of_component(self, component: str) -> Listed | None:
        return next((a for a in self.analyses if a.component == component), None)

    def holds(self, folder: str | None) -> bool:
        """Whether an analysis holds what lies in `folder` of the location, `None` its
        top: the one analysis at the top where nothing is listed, and a listed one's
        folder where the project lists them."""
        return folder is None if not self.several else self.of_folder(folder) is not None

    def named(self, folder: str | None) -> str:
        """How the analysis in `folder` is named in a message."""
        listed = self.of_folder(folder)
        return f"the analysis of {listed.component}" if listed is not None else "the analysis"

    def kept(self) -> list[str | None]:
        """The folder of each analysis the project keeps: each listed one's, or `None`, the
        location's top, where it lists none."""
        return [a.folder for a in self.analyses] if self.several else [None]

    def goals(self, folder: str | None) -> dict[str, str]:
        """Each area's goal of the analysis in `folder`, `None` the top, by the area's
        folder name (DEC-003 point 8)."""
        if not self.several:
            return dict(self.areas) if folder is None else {}
        listed = self.of_folder(folder)
        return dict(listed.areas) if listed is not None else {}

    def goals_at(self, folder: str | None) -> str:
        """Where the goals of the analysis in `folder` are written in the settings file."""
        listed = self.of_folder(folder)
        return at(CONFIG, f"/{KEY}/{listed.index}/{AREAS}" if listed else f"/{AREAS}")


class Unnamed(Exception):
    """`--analysis` names no analysis the project keeps, or names none where it must."""


def folder_named(listing: Listing, named: str | None, to: str) -> str | None:
    """The folder of the location the analysis `named` — by its component, as
    `--analysis` names it — lies in, `None` for the one analysis at the top where the
    project lists none. Raises Unnamed where it names none the project lists, or none
    where the project lists several: a command names the analysis it acts on (DEC-001
    point 2; DEC-003 point 6). `to` says what the analysis is named for, such as `to
    write in`."""
    components = ", ".join(a.component for a in listing.analyses)
    if not listing.several:
        if named is None:
            return None
        raise Unnamed(
            f"--analysis {named}: the project lists no analyses in {CONFIG}, so it keeps one, "
            f"at the top of the analysis location — leave --analysis out, or list its "
            f"analyses, one per component (DEC-001 point 2)"
        )
    if named is None:
        if len(listing.analyses) == 1:
            return listing.analyses[0].folder
        raise Unnamed(
            f"the project lists several analyses ({components}): name the one {to}, "
            f"--analysis <component> (DEC-001 point 2)"
        )
    listed = listing.of_component(named)
    if listed is None:
        raise Unnamed(
            f"--analysis {named} is no analysis the project lists in {CONFIG} ({components}) "
            f"— name one of them, or list it first (DEC-001 point 2)"
        )
    return listed.folder


def read(root: Path) -> Listing:
    """The analyses the settings file at `root` lists. No file, a file that does not
    parse, or no list, lists none: the numbering setting's reading reports a file that
    does not parse (`_lib/numbering.py`), and `pkit validate` a list of another shape."""
    path = root / CONFIG
    if not path.is_file():
        return Listing()
    try:
        config: Any = markdown.load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError):
        return Listing()
    listed = config.get(KEY) if isinstance(config, Mapping) else None
    analyses: list[Listed] = []
    for index, item in enumerate(listed if isinstance(listed, list) else []):
        entry = _listed(index, item)
        if entry is not None:
            analyses.append(entry)
    top = _goals(config.get(AREAS)) if isinstance(config, Mapping) else ()
    problems = _problems(analyses)
    if analyses and isinstance(config, Mapping) and AREAS in config:
        problems.append(
            Finding(
                ERROR,
                at(CONFIG, f"/{AREAS}"),
                f"the project lists its analyses in `{KEY}`, so the file's own `{AREAS}` belongs "
                f"to no analysis: each analysis keeps its areas' goals in its entry's `{AREAS}` "
                f"(DEC-003 point 8) — move them there",
            )
        )
    keeps = not (isinstance(config, Mapping) and config.get(OVERVIEW) is False)
    return Listing(tuple(analyses), tuple(problems), top, keeps)


def _goals(value: object) -> tuple[tuple[str, str], ...]:
    """Each area's goal as written, by its folder name; entries of another shape are left
    out, for the schema to report."""
    if not isinstance(value, Mapping):
        return ()
    return tuple(
        (area, " ".join(goal.split()))
        for area, goal in value.items()
        if isinstance(area, str) and _AREA.match(area) and isinstance(goal, str) and goal.strip()
    )


def _listed(index: int, item: object) -> Listed | None:
    if not isinstance(item, Mapping):
        return None
    component, folder = item.get("component"), item.get("folder")
    word = schemas.slug_pattern()
    if not (isinstance(component, str) and word.match(component)):
        return None
    if not (isinstance(folder, str) and word.match(folder)):
        return None
    raw = item.get(HEAD)
    builds_on = []
    for position, entry in enumerate(raw if isinstance(raw, list) else []):
        name = entry.get("analysis") if isinstance(entry, Mapping) else None
        optional = entry.get("optional", False) if isinstance(entry, Mapping) else None
        if isinstance(name, str) and word.match(name) and isinstance(optional, bool):
            builds_on.append(BuildsOn(name, optional, position))
    return Listed(index, component, folder, tuple(builds_on), _goals(item.get(AREAS)))


def _problems(analyses: Sequence[Listed]) -> list[Finding]:
    found: list[Finding] = []
    components: dict[str, Listed] = {}
    folders: dict[str, Listed] = {}
    for listed in analyses:
        if listed.component in components:
            found.append(
                Finding(
                    ERROR,
                    listed.where,
                    f"{listed.component} is listed twice, here and at "
                    f"{components[listed.component].where}: a component keeps one analysis "
                    f"(DEC-001 point 2) — remove one entry",
                )
            )
        components.setdefault(listed.component, listed)
        if listed.folder in folders:
            found.append(
                Finding(
                    ERROR,
                    listed.where,
                    f"the folder {listed.folder} is listed twice, here and at "
                    f"{folders[listed.folder].where}: each analysis takes a folder of its own "
                    f"(DEC-001 point 2)",
                )
            )
        folders.setdefault(listed.folder, listed)
        seen: set[str] = set()
        for entry in listed.builds_on:
            if entry.analysis == listed.component:
                found.append(
                    Finding(
                        ERROR,
                        listed.builds_on_at(entry),
                        f"the analysis of {listed.component} builds on itself: an analysis "
                        f"builds on the analyses of the components its component depends on "
                        f"(DEC-001 point 2) — remove the entry",
                    )
                )
            elif entry.analysis in seen:
                found.append(
                    Finding(
                        ERROR,
                        listed.builds_on_at(entry),
                        f"{entry.analysis} is named twice: name each analysis it builds on once",
                    )
                )
            seen.add(entry.analysis)
    return found


# --- what a head takes from another analysis --------------------------------------------------


@dataclass(frozen=True)
class TakenActor:
    """An actor a head lists from another analysis: its id there, its name, and the
    needs it brings to this analysis (DEC-001 point 2)."""

    id: str
    name: str
    needs: tuple[str, ...]


@dataclass(frozen=True)
class Taken:
    """What a head takes from one analysis it builds on: that analysis's component, the
    version its links name, and the terms, by id and name, and the actors it lists."""

    index: int
    analysis: str
    version: str
    terms: tuple[tuple[str, str], ...]
    actors: tuple[TakenActor, ...]

    def actor(self, actor_id: str) -> TakenActor | None:
        return next((a for a in self.actors if a.id == actor_id), None)


@dataclass(frozen=True)
class Head:
    """A glossary's head data: the glossary's path, what it takes from each analysis it
    builds on, in written order, and the raw value, which its schema judges."""

    path: str
    taken: tuple[Taken, ...]
    raw: Any

    def of(self, analysis: str) -> Taken | None:
        return next((t for t in self.taken if t.analysis == analysis), None)


def glossary_of(analysis: Analysis, folder: str | None) -> str | None:
    """The path of the glossary of the analysis in `folder`, `None` the top's, as its
    place gives it; `None` where the reading places no glossary."""
    for path, kind in analysis.files.items():
        if kind == TERM and analysis.folders.get(path) == folder:
            return path
    return None


def head(analysis: Analysis, folder: str | None) -> Head | None:
    """The head data of the glossary of the analysis in `folder`; `None` where that
    analysis has no glossary, or its glossary's front matter holds no `builds-on`.
    Entries of another shape are left out, for the schema to report."""
    path = glossary_of(analysis, folder)
    if path is None:
        return None
    fields = analysis.glossaries.get(path)
    if not isinstance(fields, Mapping) or HEAD not in fields:
        return None
    raw = fields.get(HEAD)
    taken: list[Taken] = []
    for index, item in enumerate(raw if isinstance(raw, list) else []):
        if not isinstance(item, Mapping):
            continue
        name, version = item.get("analysis"), item.get("version")
        if not isinstance(name, str) or not isinstance(version, (str, int, float)):
            continue
        terms = tuple(
            (str(t["id"]), str(t["name"]))
            for t in _mappings(item.get("terms"))
            if isinstance(t.get("id"), str) and isinstance(t.get("name"), str)
        )
        actors = tuple(
            TakenActor(
                str(a["id"]),
                str(a["name"]),
                tuple(n for n in (a.get("needs") or []) if isinstance(n, str)),
            )
            for a in _mappings(item.get("actors"))
            if isinstance(a.get("id"), str) and isinstance(a.get("name"), str)
        )
        taken.append(Taken(index, name, str(version), terms, actors))
    return Head(path, tuple(taken), raw)


def _mappings(value: object) -> list[Mapping[str, Any]]:
    return [v for v in value if isinstance(v, Mapping)] if isinstance(value, list) else []


def actor_problem(
    listing: Listing, analysis: Analysis, reference: str, folder: str | None
) -> str | None:
    """Why an artefact in `folder` cannot name `reference`, an actor of another
    analysis written with that analysis, such as `core:ACT-developer`, or `None` when it
    can: its analysis is listed, builds on that one, and its glossary's head lists the
    actor from it (DEC-001 points 2 and 4)."""
    other, actor_id = qualified(reference)
    if other is None:
        return None
    listed = listing.of_folder(folder)
    if listed is None:
        return (
            f"{reference} is an actor of the analysis of {other}, and only an analysis the "
            f"capability's configuration lists builds on another (DEC-001 point 2)"
        )
    if listed.built_on(other) is None:
        return (
            f"{reference} is an actor of the analysis of {other}, which the analysis of "
            f"{listed.component} does not build on: an analysis names only the analyses it "
            f"builds on, which `{KEY}` lists in {CONFIG} (DEC-001 point 2)"
        )
    taken = head(analysis, folder)
    found = taken.of(other) if taken is not None else None
    if found is None or found.actor(actor_id) is None:
        return (
            f"{reference} is no {NOUN[ACTOR]} the head of the glossary of the analysis of "
            f"{listed.component} lists from {other}: list it under `{HEAD}`, with its name and "
            f"the needs it brings here (DEC-001 point 2)"
        )
    return None


# --- what a component declares it depends on ---------------------------------------------------


@dataclass(frozen=True)
class Declared:
    """What a component's package metadata says it depends on: each analysis by its
    component's name, whether it is optional, and the lowest version it needs (`None`
    where it names none), with the file that says so."""

    file: str
    depends: Mapping[str, tuple[bool, str | None]]


def declared(root: Path, component: str) -> Declared | None:
    """The dependencies `component` declares in its package metadata, where the repository
    holds that metadata as a capability's; `None` elsewhere, so the configuration's list
    is the project's statement of them. The backbone declares none here."""
    if component == BACKBONE:
        return None
    rel = PACKAGE.format(name=component)
    path = root / rel
    if not path.is_file():
        return None
    try:
        package: Any = markdown.load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError):
        return None
    if not isinstance(package, Mapping):
        return None
    depends: dict[str, tuple[bool, str | None]] = {}
    backbone = package.get("requires_backbone")
    if isinstance(backbone, str):
        depends[BACKBONE] = (False, floor(backbone))
    for entry in _mappings(package.get("requires_capabilities")):
        name, version = entry.get("name"), entry.get("version")
        if isinstance(name, str):
            depends[name] = (
                entry.get("optional") is True,
                floor(version) if isinstance(version, str) else None,
            )
    return Declared(rel, depends)


def floor(declared_range: str) -> str | None:
    """The lowest version a range admits, its `>=` bound: `1.149.0` of `>=1.149.0,<2.0.0`;
    `None` where it gives no such bound."""
    for bound in declared_range.split(","):
        found = _FLOOR.match(bound)
        if found is not None:
            return found["version"]
    return None


def same_version(written: str, wanted: str) -> bool:
    """Whether a head's version names `wanted`, a leading `v` read as part of neither."""
    return written.strip().removeprefix("v") == wanted.strip().removeprefix("v")
