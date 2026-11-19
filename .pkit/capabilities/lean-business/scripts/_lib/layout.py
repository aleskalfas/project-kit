"""An idea's folder, and the place of each of its files (lean-business DEC-002 point 2).

The location holds one folder for each idea, named by the idea's id:

    <location>/<idea>/goal.yaml                            lean-business:goal
    <location>/<idea>/variants/<variant>/canvas.yaml       lean-business:canvas
    <location>/<idea>/variants/<variant>/assumptions.yaml  lean-business:assumptions
    <location>/<idea>/experiments/<experiment>.yaml        lean-business:experiment
    <location>/<idea>/cycles/<cycle>.yaml                  lean-business:cycle

A kind with many files takes a folder of its own, which appears only once something goes
into it. A folder's name, and an experiment's or a cycle's file name without `.yaml`, is the
subject's own part of its id (`ids`). Each file names its schema in `pkit_schema` (COR-023).

`read` lists what the location holds, as it lies: the files at each place, each read as its
value, and each file of the capability's that lies where the layout gives it no place, or
at a place that takes another schema. Hidden files and folders and links are passed over,
and a file that is not YAML, or names no schema of the capability's and lies at no place, is
none of the capability's.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _lib import ids
from _lib.reading import ReadError, read_yaml
from _lib.root import CAPABILITY

GOAL = "goal.yaml"
VARIANTS = "variants"
CANVAS = "canvas.yaml"
ASSUMPTIONS = "assumptions.yaml"
EXPERIMENTS = "experiments"
CYCLES = "cycles"
SUFFIX = ".yaml"

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


def read(root: Path, location: str) -> Contents:
    """What the location `location`, relative to `root`, holds. Nothing where its folder
    does not exist yet."""
    contents = Contents()
    top = root / location
    if not top.is_dir() or top.is_symlink():
        return contents
    for rel in _files(root, top):
        parts = Path(rel).relative_to(location).parts
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
        idea = contents.ideas.setdefault(idea_name, Idea(idea_name, f"{location}/{idea_name}"))
        found = _read(root, rel, kind)
        if kind == "goal":
            idea.goal = found
        elif kind in ("canvas", "assumptions"):
            assert own is not None
            variant = idea.variants.setdefault(own, Variant(own))
            if kind == "canvas":
                variant.canvas = found
            else:
                variant.assumptions = found
        elif kind == "experiment":
            assert own is not None
            idea.experiments[own] = found
        else:
            assert own is not None
            idea.cycles[own] = found
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
    try:
        data = read_yaml(root / rel)
    except ReadError:
        return
    named = data.get("pkit_schema") if isinstance(data, Mapping) else None
    if isinstance(named, str) and named.startswith(f"{CAPABILITY}:"):
        contents.strays.append(
            Stray(
                rel, f"names `{named}`, but lies where the layout gives no file of the capability"
            )
        )


def _files(root: Path, top: Path) -> list[str]:
    """The files under `top`, relative to `root`, in path order, with hidden files and
    folders and links passed over."""
    found: list[str] = []
    for current, dirs, names in os.walk(top, followlinks=False):
        here = Path(current)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not (here / d).is_symlink())
        for name in names:
            path = here / name
            if name.startswith(".") or path.is_symlink() or not path.is_file():
                continue
            found.append(path.relative_to(root).as_posix())
    return sorted(found)
