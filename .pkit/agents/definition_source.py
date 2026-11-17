"""Which definition of each name is the agent (COR-013 point 8, COR-017, ADR-087).

The project, an installed capability and core may each ship a definition of one
name. At most one of them is the agent of that name, and every part that
deploys, runs, checks or names an agent asks this module which one, so none
runs one definition while another checks a different one.

**The places and their order.** The project's place, `.pkit/agents/project/`,
wins over every other. Then each capability's, `.pkit/capabilities/<name>/agents/`,
and last core's, `.pkit/agents/core/`. Between two capabilities, the one the
project chose for the name wins, else the first by name, comparing names by
their characters' code points, so every machine takes the same one.

**A definition** is its place and its name. A place ships it as the canonical
file alone, `<name>.md`, or in a folder, `<name>/<name>.md` (COR-015). A folder
without its canonical file ships none. A capability's definition counts while
the component registry records the capability, whatever its folder holds, and
the project has not skipped it. The project's and core's always count.

**Its answer** (`pick`), for every name some place ships, in one call: the
definition that is the agent, with its file and its place; whether it is
refused before its text is read, since its place holds both layouts; or why the
name has none; every definition of the name, each with whether it counts and
why not; each collision between two capabilities no choice settles, with the
capability that won it; each choice that decides nothing, with why; or that it
cannot tell. A refused agent stays the agent: no other definition stands in.

**What it cannot tell.** It learns which capabilities are installed, their
skips and the project's choices from the lifecycle area's reader,
`.pkit/lifecycle/capability_records.py`, loaded from the tree this module was
loaded from. An unreadable registry leaves it unable to tell any name a
capability's folder ships; unreadable choices, any name two or more counting
capabilities ship; one capability's unreadable manifest, the names that
capability's folder ships. A name the project ships is told in each case,
since it wins whatever the records say.

It parses no definition: it reads which files exist, and the bytes of a
canonical file for its digest (`digest`), the value a deploy's mark records.

Propagated neutral code at the root of the agents area, beside the reader of an
agent's tool access. Only the standard library at module level. A caller loads
it from its file, without adding the area to Python's import path and without
writing bytecode into the tree. A function keeps its name and its answer: one
whose answer changes takes a new name (ADR-087 point 5).
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple

#: The project's place and core's. A capability's place is `capability:<name>`
#: (`capability_place`).
PROJECT = "project"
CORE = "core"
_CAPABILITY_PREFIX = "capability:"

#: The lifecycle area's reader of the records, beside this module's area in the
#: tree it was loaded from (ADR-087 point 1).
RECORDS_READER = Path(__file__).resolve().parent.parent / "lifecycle" / "capability_records.py"

#: The digest a deploy's mark records: the algorithm's name, a colon, the hex digest.
DIGEST_ALGORITHM = "sha256"


class RecordsUnreachable(Exception):
    """The lifecycle's reader of the records cannot be loaded; the message says why."""


class Definition(NamedTuple):
    """One place's definition of a name.

    `files` are its canonical files, one for each layout the place holds, the
    file alone before the folder's. `counts` is False for a capability's
    definition whose capability is not installed, whose definition the project
    skipped, or whose records cannot be read, and `why_not` says which.
    """

    name: str
    place: str
    files: tuple[Path, ...]
    counts: bool = True
    why_not: str | None = None

    @property
    def both_layouts(self) -> bool:
        """True where the place holds both layouts of the name, so two texts."""
        return len(self.files) > 1


class Pick(NamedTuple):
    """Which definition of one name is the agent.

    `agent` is that definition. Where its place holds both layouts, `refused`
    says so: it is still the agent, and no other definition stands in. Where
    the name has no agent, `none` says why. Where the records that decide it
    cannot be read, `untold` says why, and `agent` is None. `definitions` are
    every definition of the name, in the order of their places.
    """

    name: str
    definitions: tuple[Definition, ...]
    agent: Definition | None = None
    refused: str | None = None
    none: str | None = None
    untold: str | None = None

    @property
    def file(self) -> Path | None:
        """The agent's one canonical file, or None where it has no one text."""
        if self.agent is None or self.refused is not None:
            return None
        return self.agent.files[0]


class Collision(NamedTuple):
    """A name two or more counting capabilities ship, which no choice settles."""

    name: str
    capabilities: tuple[str, ...]
    winner: str


class IdleChoice(NamedTuple):
    """A choice the project recorded that decides nothing, and why."""

    name: str
    capability: str
    why: str


class Answer(NamedTuple):
    """Which definition of every name some place ships is the agent."""

    picks: Mapping[str, Pick]
    collisions: tuple[Collision, ...] = ()
    idle_choices: tuple[IdleChoice, ...] = ()


def capability_place(capability: str) -> str:
    """The place of capability *capability*'s definitions."""
    return f"{_CAPABILITY_PREFIX}{capability}"


def place_capability(place: str) -> str | None:
    """The capability whose place *place* is, or None for the project's and core's."""
    if place.startswith(_CAPABILITY_PREFIX):
        return place[len(_CAPABILITY_PREFIX) :]
    return None


def place_folder(tree: Path, place: str) -> Path:
    """The folder of *place*'s definitions in the project at *tree*."""
    pkit = Path(tree) / ".pkit"
    capability = place_capability(place)
    if capability is not None:
        return pkit / "capabilities" / capability / "agents"
    return pkit / "agents" / place


def describe(place: str) -> str:
    """*place* in words: `the project`, `core`, or `capability <name>`."""
    capability = place_capability(place)
    if capability is not None:
        return f"capability {capability}"
    return "the project" if place == PROJECT else place


def pick(tree: Path) -> Answer:
    """Which definition of every name some place ships is the agent, in the
    project at *tree*, the folder holding its `.pkit/`.

    Raises `RecordsUnreachable` where the lifecycle's reader of the records,
    beside this module's area, cannot be loaded.
    """
    tree = Path(tree)
    records = _records_reader().read_records(tree)
    capability_folders = _capability_folders(tree, records)
    shipped: dict[str, dict[str, tuple[Path, ...]]] = {}
    for place in (PROJECT, *map(capability_place, capability_folders), CORE):
        for name, files in _shipped_in(place_folder(tree, place)).items():
            shipped.setdefault(name, {})[place] = files

    picks: dict[str, Pick] = {}
    collisions: list[Collision] = []
    for name in sorted(shipped):
        decided, collision = _pick_one(name, shipped[name], records)
        picks[name] = decided
        if collision is not None:
            collisions.append(collision)
    return Answer(
        picks=picks,
        collisions=tuple(collisions),
        idle_choices=_idle_choices(records, shipped),
    )


def digest(path: Path) -> str:
    """The digest of the file at *path*, as a deploy's mark records it: SHA-256 of
    its bytes, written `sha256:<hex>`."""
    return f"{DIGEST_ALGORITHM}:{hashlib.sha256(Path(path).read_bytes()).hexdigest()}"


# --- internals ------------------------------------------------------------------


def _records_reader() -> ModuleType:
    """The lifecycle's reader of the records, loaded from its file beside this
    module's area, writing no bytecode into the tree."""
    if not RECORDS_READER.is_file():
        raise RecordsUnreachable(f"{RECORDS_READER} is not there")
    spec = importlib.util.spec_from_file_location(
        "pkit_lifecycle_capability_records", RECORDS_READER
    )
    if spec is None or spec.loader is None:
        raise RecordsUnreachable(f"{RECORDS_READER} cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise RecordsUnreachable(f"{RECORDS_READER} cannot be loaded: {exc}") from None
    finally:
        sys.dont_write_bytecode = previous
    if not callable(getattr(module, "read_records", None)):
        raise RecordsUnreachable(f"{RECORDS_READER} has no read_records")
    return module


def _capability_folders(tree: Path, records: Any) -> list[str]:
    """Every capability with a folder on disk, or recorded in the registry, by
    code points."""
    names = {capability.name for capability in records.capabilities}
    root = tree / ".pkit" / "capabilities"
    if root.is_dir():
        names.update(
            entry.name for entry in root.iterdir() if entry.is_dir() and not _hidden(entry.name)
        )
    return sorted(names)


def _shipped_in(folder: Path) -> dict[str, tuple[Path, ...]]:
    """Each name a place's folder ships, with its canonical files: the file
    alone, then the folder's, for each layout the folder holds."""
    found: dict[str, list[Path]] = {}
    if not folder.is_dir():
        return {}
    for entry in folder.iterdir():
        if _hidden(entry.name):
            continue
        if entry.suffix == ".md" and entry.is_file():
            found.setdefault(entry.stem, []).insert(0, entry)
        elif entry.is_dir() and (entry / f"{entry.name}.md").is_file():
            found.setdefault(entry.name, []).append(entry / f"{entry.name}.md")
    return {name: tuple(files) for name, files in found.items()}


def _hidden(name: str) -> bool:
    return name.startswith(".")


def _capability_definition(
    name: str, place: str, files: tuple[Path, ...], records: Any
) -> tuple[Definition, str | None]:
    """A capability's definition of *name*, and why the records that decide whether
    it counts cannot be read, if they cannot."""
    capability = place_capability(place) or ""
    if records.registry_unreadable is not None:
        return Definition(
            name, place, files, False, records.registry_unreadable
        ), records.registry_unreadable
    if capability not in records.installed:
        why = f"capability {capability} is not installed: the component registry does not record it"
        return Definition(name, place, files, False, why), None
    recorded = records.skips.get(capability)
    if recorded is not None and recorded.unreadable is not None:
        return Definition(name, place, files, False, recorded.unreadable), recorded.unreadable
    if recorded is not None and recorded.skips_agent(name):
        why = f"the project skipped capability {capability}'s agent {name}"
        return Definition(name, place, files, False, why), None
    return Definition(name, place, files), None


def _pick_one(
    name: str, at: Mapping[str, tuple[Path, ...]], records: Any
) -> tuple[Pick, Collision | None]:
    """The pick of *name*, shipped at each place of *at*, and the collision no
    choice settles, if any."""
    project = Definition(name, PROJECT, at[PROJECT]) if PROJECT in at else None
    core = Definition(name, CORE, at[CORE]) if CORE in at else None
    capabilities: list[Definition] = []
    untold: str | None = None
    for place in sorted(at, key=lambda place: place_capability(place) or ""):
        if place_capability(place) is None:
            continue
        definition, unreadable = _capability_definition(name, place, at[place], records)
        capabilities.append(definition)
        untold = untold or unreadable
    definitions = tuple(d for d in (project, *capabilities, core) if d is not None)

    if project is not None:
        return _the_agent(name, definitions, project), None
    if untold is not None:
        return Pick(name, definitions, untold=f"cannot tell which is the agent: {untold}"), None

    counting = [d for d in capabilities if d.counts]
    if len(counting) > 1 and records.choices_unreadable is not None:
        why = f"cannot tell which is the agent: {records.choices_unreadable}"
        return Pick(name, definitions, untold=why), None
    chosen = records.choices.get(name)
    winner = next((d for d in counting if place_capability(d.place) == chosen), None)
    collision: Collision | None = None
    if winner is None and counting:
        winner = counting[0]
        if len(counting) > 1:
            names = tuple(place_capability(d.place) or "" for d in counting)
            collision = Collision(name, names, names[0])
    winner = winner or core
    if winner is not None:
        return _the_agent(name, definitions, winner), collision
    uncounted = "; ".join(f"{describe(d.place)}'s, since {d.why_not}" for d in definitions)
    return Pick(name, definitions, none=f"no definition of it counts: {uncounted}"), None


def _the_agent(name: str, definitions: tuple[Definition, ...], agent: Definition) -> Pick:
    """The pick whose agent is *agent*, refused where its place holds both layouts."""
    refused = None
    if agent.both_layouts:
        refused = (
            f"{describe(agent.place)} ships two texts of it, {name}.md and {name}/{name}.md, "
            "so its definition is refused (COR-013 point 8): keep one"
        )
    return Pick(name, definitions, agent=agent, refused=refused)


def _idle_choices(
    records: Any, shipped: Mapping[str, Mapping[str, tuple[Path, ...]]]
) -> tuple[IdleChoice, ...]:
    """Each choice that decides nothing: of a capability not installed, one that
    does not ship the name, or one whose definition of it the project skipped."""
    if records.registry_unreadable is not None:
        return ()
    idle: list[IdleChoice] = []
    for name, capability in sorted(records.choices.items()):
        recorded = records.skips.get(capability)
        if capability not in records.installed:
            why = f"capability {capability} is not installed"
        elif capability_place(capability) not in shipped.get(name, {}):
            why = f"capability {capability} ships no agent named {name}"
        elif recorded is not None and recorded.unreadable is None and recorded.skips_agent(name):
            why = f"the project skipped capability {capability}'s agent {name}"
        else:
            continue
        idle.append(IdleChoice(name, capability, why))
    return tuple(idle)
