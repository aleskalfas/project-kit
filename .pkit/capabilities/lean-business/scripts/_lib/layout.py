"""An idea's folder, and the place of each of its files (lean-business DEC-002 points 1 and 2).

The location holds one folder for each idea, named by the idea's id:

    <location>/<idea>/goal.yaml                            lean-business:goal
    <location>/<idea>/variants/<variant>/canvas.yaml       lean-business:canvas
    <location>/<idea>/variants/<variant>/assumptions.yaml  lean-business:assumptions
    <location>/<idea>/experiments/<experiment>.yaml        lean-business:experiment
    <location>/<idea>/cycles/<cycle>.yaml                  lean-business:cycle

A kind with many files takes a folder of its own, which appears only once something goes
into it. A folder's name, and an experiment's or a cycle's file name without `.yaml`, is the
subject's own part of its id (`ids`). Each file names its schema in `pkit_schema` (COR-023).

- **What a location holds** (`read`), as it lies: the files at each place, each read as
  its value, and each file of the capability's that lies where the layout gives it no
  place, at a place that takes another schema, or at a place but ending in `.yml`, which
  no validation reads. The files are those git sees (`listing`). Hidden files and folders
  and links are passed over, and a file that is not YAML, or names no schema of the
  capability's and lies at no place, is none of the capability's. `read` takes one idea's
  folder alone where it is named.
- **Where a subject's file lies** (`path_of`), the inverse: from a kind and an id to the
  path the layout puts it at, refusing an id the id patterns refuse.
- **A file of the capability's outside the location** (`outside`): one the backbone's
  data validation reads, and the check would never see, since an idea's files lie in the
  location (DEC-002 point 1).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from _lib import ids, listing
from _lib.reading import ReadError, load_yaml, read_yaml
from _lib.root import CAPABILITY, CONFIG

GOAL = "goal.yaml"
VARIANTS = "variants"
CANVAS = "canvas.yaml"
ASSUMPTIONS = "assumptions.yaml"
EXPERIMENTS = "experiments"
CYCLES = "cycles"
SUFFIX = ".yaml"

#: The suffix YAML is often written with, which the layout's places and the backbone's data
#: validation do not read.
OTHER_SUFFIX = ".yml"

#: The schema each place takes, by the kind of file it holds.
SCHEMA = {
    "goal": f"{CAPABILITY}:goal",
    "canvas": f"{CAPABILITY}:canvas",
    "assumptions": f"{CAPABILITY}:assumptions",
    "experiment": f"{CAPABILITY}:experiment",
    "cycle": f"{CAPABILITY}:cycle",
}

#: Each kind of file, in words.
WHAT = {
    "goal": "the idea's goal",
    "canvas": "a variant's canvas",
    "assumptions": "a variant's assumptions",
    "experiment": "an experiment",
    "cycle": "a cycle",
}

#: The configuration's schema, the one file of the capability's that lies outside the
#: location.
CONFIG_SCHEMA = f"{CAPABILITY}:config"

#: The methodology's own folder, and the name of a folder in it that holds a project's own
#: files, which the backbone's data validation reads as the project's data.
KIT_DIR = ".pkit"
PROJECT_DIR = "project"


class IdRefused(Exception):
    """An id that names no place of the layout: one the id patterns refuse, or of a kind the
    layout has no place for."""


@dataclass
class File:
    """A file at a place of the layout: its path relative to the project root, and its
    value where it reads as a mapping bound to its place's schema. `problem` says why it
    does not, where it does not."""

    rel: str
    data: Mapping[str, Any] | None = None
    problem: str | None = None
    unreadable: bool = False


@dataclass
class Variant:
    """A variant's folder: its name, and its canvas and assumptions where it holds them."""

    name: str
    canvas: File | None = None
    assumptions: File | None = None


@dataclass
class Idea:
    """An idea's folder: its name, its path relative to the project root, and its files."""

    name: str
    rel: str
    goal: File | None = None
    variants: dict[str, Variant] = field(default_factory=dict)
    experiments: dict[str, File] = field(default_factory=dict)
    cycles: dict[str, File] = field(default_factory=dict)


@dataclass(frozen=True)
class Stray:
    """A file or folder the layout gives no place, or a name that is no id: its path
    relative to the project root, and why."""

    rel: str
    why: str


@dataclass
class Contents:
    """What a location holds: its ideas, by name, and what lies astray."""

    ideas: dict[str, Idea] = field(default_factory=dict)
    strays: list[Stray] = field(default_factory=list)


# --- what a location holds -----------------------------------------------------------------------


def read(root: Path, location: str, idea: str | None = None) -> Contents:
    """What the location `location`, relative to `root`, holds, or the folder of the idea
    `idea` alone where it is named. Nothing where the folder does not exist yet. Raises
    listing.ListingFailed where git cannot list the files, and IdRefused for an idea named
    by no id."""
    contents = Contents()
    if idea is not None and not ids.is_segment(idea):
        raise IdRefused(f"`{idea}` is no idea's id")
    folder = f"{location}/{idea}" if idea is not None else location
    top = root / folder
    if not top.is_dir() or top.is_symlink():
        return contents
    for rel in listing.files(root, folder):
        parts = PurePosixPath(rel).relative_to(location).parts
        if listing.hidden(PurePosixPath(*parts).as_posix()):
            continue
        if parts[-1].endswith(OTHER_SUFFIX):
            _other_suffix(root, rel, parts, contents)
            continue
        place = _place(parts)
        if place is None:
            _astray(root, rel, contents)
            continue
        kind, idea_name, own = place
        if not ids.is_segment(idea_name):
            contents.strays.append(
                Stray(f"{location}/{idea_name}", "the idea's folder is named by no id")
            )
            continue
        if own is not None and not ids.is_segment(own):
            contents.strays.append(Stray(rel, f"the {kind}'s own name, `{own}`, is no id"))
            continue
        found = _read(root, rel, kind)
        held = contents.ideas.setdefault(idea_name, Idea(idea_name, f"{location}/{idea_name}"))
        if kind == "goal":
            held.goal = found
        elif kind in ("canvas", "assumptions"):
            assert own is not None
            variant = held.variants.setdefault(own, Variant(own))
            if kind == "canvas":
                variant.canvas = found
            else:
                variant.assumptions = found
        elif kind == "experiment":
            assert own is not None
            held.experiments[own] = found
        else:
            assert own is not None
            held.cycles[own] = found
    contents.strays = list(dict.fromkeys(contents.strays))
    return contents


def _place(parts: tuple[str, ...]) -> tuple[str, str, str | None] | None:
    """The kind of file the layout puts at `parts`, a path within the location, with the
    idea's folder and the subject's own name: None where the layout puts none there."""
    if len(parts) == 2 and parts[1] == GOAL:
        return "goal", parts[0], None
    if len(parts) == 4 and parts[1] == VARIANTS and parts[3] in (CANVAS, ASSUMPTIONS):
        return ("canvas" if parts[3] == CANVAS else "assumptions"), parts[0], parts[2]
    if len(parts) == 3 and parts[1] in (EXPERIMENTS, CYCLES) and parts[2].endswith(SUFFIX):
        kind = "experiment" if parts[1] == EXPERIMENTS else "cycle"
        return kind, parts[0], parts[2][: -len(SUFFIX)]
    return None


def _read(root: Path, rel: str, kind: str) -> File:
    try:
        data = read_yaml(root / rel)
    except ReadError as exc:
        return File(rel, problem=str(exc).replace(f"{root / rel}: ", ""), unreadable=True)
    expected = SCHEMA[kind]
    if not isinstance(data, Mapping):
        return File(rel, problem=f"is no mapping, where the layout puts {WHAT[kind]}, `{expected}`")
    named = data.get("pkit_schema")
    if named != expected:
        said = "names no schema" if named is None else f"names `{named}`"
        return File(
            rel, problem=f"lies where the layout puts {WHAT[kind]}, but {said}, not `{expected}`"
        )
    return File(rel, data=data)


def _astray(root: Path, rel: str, contents: Contents) -> None:
    """Note `rel` astray where it is a file of the capability's: YAML that names one of its
    schemas."""
    if not rel.endswith(SUFFIX):
        return
    named = _schema_named(root, rel)
    if named is not None:
        contents.strays.append(
            Stray(
                rel, f"names `{named}`, but lies where the layout gives no file of the capability"
            )
        )


def _other_suffix(root: Path, rel: str, parts: tuple[str, ...], contents: Contents) -> None:
    """Note `rel`, which ends in `.yml`, astray where it lies at a place of the layout once
    its suffix is `.yaml`, or names a schema of the capability's."""
    swapped = (*parts[:-1], parts[-1][: -len(OTHER_SUFFIX)] + SUFFIX)
    if _place(swapped) is None and _schema_named(root, rel) is None:
        return
    contents.strays.append(
        Stray(
            rel,
            f"it ends in `{OTHER_SUFFIX}`, and the layout's files end in `{SUFFIX}`: no "
            f"validation reads it, so rename it to `{swapped[-1]}`",
        )
    )


def _schema_named(root: Path, rel: str) -> str | None:
    """The schema of the capability's the YAML file `rel` names, or None."""
    try:
        raw = (root / rel).read_bytes()
    except OSError:
        return None
    if f"{CAPABILITY}:".encode() not in raw:
        return None
    try:
        data = load_yaml(raw.decode("utf-8"), rel)
    except (ReadError, UnicodeDecodeError):
        return None
    named = data.get("pkit_schema") if isinstance(data, Mapping) else None
    return named if isinstance(named, str) and named.startswith(f"{CAPABILITY}:") else None


# --- where a subject's file lies -----------------------------------------------------------------

#: The kinds `path_of` places, each with the id the kind's subjects carry.
_KINDS = {
    "goal": ids.SEGMENT,
    "canvas": ids.IDEA_QUALIFIED,
    "assumptions": ids.IDEA_QUALIFIED,
    "experiment": ids.IDEA_QUALIFIED,
    "cycle": ids.IDEA_QUALIFIED,
}


def path_of(location: str, kind: str, qualified: str) -> str:
    """The path, relative to the project root, where the layout puts the file of `kind`
    whose subject is `qualified`: an idea's id for its goal, a variant's for its canvas and
    its assumptions, an experiment's or a cycle's for its own file. Raises IdRefused for a
    kind the layout has no place for, or an id that is not of the kind's form."""
    if kind not in _KINDS:
        raise IdRefused(f"the layout has no place for a file of the kind `{kind}`")
    if kind == "goal":
        if not ids.is_segment(qualified):
            raise IdRefused(f"`{qualified}` is no idea's id")
        return f"{location}/{qualified}/{GOAL}"
    if not ids.is_idea_qualified(qualified):
        raise IdRefused(f"`{qualified}` is no id of {WHAT[kind]}'s subject, `<idea>--<own>`")
    idea, own = ids.idea_of(qualified), ids.own(qualified)
    if kind in ("canvas", "assumptions"):
        name = CANVAS if kind == "canvas" else ASSUMPTIONS
        return f"{location}/{idea}/{VARIANTS}/{own}/{name}"
    folder = EXPERIMENTS if kind == "experiment" else CYCLES
    return f"{location}/{idea}/{folder}/{own}{SUFFIX}"


# --- the capability's files outside the location --------------------------------------------------


def outside(root: Path, location: str) -> list[Stray]:
    """Each file the backbone's data validation reads, outside the location, that names a
    schema of the capability's: the repository outside `.pkit/` and outside any hidden
    folder, and each project's own folder within `.pkit/`. The configuration, bound to
    `lean-business:config` where the capability keeps it, is the one such file in its
    place. Raises listing.ListingFailed where git cannot list the files."""
    found: list[Stray] = []
    for rel in listing.files(root):
        if not rel.endswith(SUFFIX) or rel.startswith(f"{location}/"):
            continue
        if not _data_validation_reads(rel):
            continue
        named = _schema_named(root, rel)
        if named is None or (rel == CONFIG and named == CONFIG_SCHEMA):
            continue
        where = (
            f"`{CONFIG}`, where the capability keeps its configuration"
            if named == CONFIG_SCHEMA
            else f"the location, `{location}`, where the check reads an idea's files"
        )
        found.append(Stray(rel, f"names `{named}`, but lies outside {where}"))
    return found


def _data_validation_reads(rel: str) -> bool:
    """Whether the backbone's data validation reads the file `rel` as a project's data."""
    folders = PurePosixPath(rel).parts[:-1]
    if folders[:1] == (KIT_DIR,):
        folders = folders[1:]
        if PROJECT_DIR not in folders:
            return False
    return not any(folder.startswith(".") for folder in folders)
