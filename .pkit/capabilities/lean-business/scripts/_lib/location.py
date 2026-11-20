"""The capability's location: the folder that holds a project's ideas, one folder for each
idea (lean-business DEC-002 point 1).

- **Its default** is `lean-business/` at the repository's top. The capability's
  configuration records it under `location:` once the first command writes an idea, so a
  later change of the default moves no recorded location (COR-049 point 5).
- **Until it is recorded** the location is read as the default.
- **Refused:** the repository's top itself, a path outside the repository, under `.pkit/`,
  under a hidden folder, reached through a link, or a file rather than a folder. An empty
  `location:` is refused too, rather than read as no location.
- **A location whose folder does not exist yet** holds no idea, which is no fault: a project
  may record its folder before its first idea.

This module reads the location, as the check and every command that only reads do. Recording
it, at a command's first write, is `writes`'s.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from _lib.reading import ReadError, read_yaml
from _lib.root import CONFIG

#: The location's default, at the repository's top.
DEFAULT = "lean-business"

#: The configuration's key that records the location.
KEY = "location"


class LocationRefused(Exception):
    """No location can be read: one the rules refuse, or a configuration that cannot be
    read."""


@dataclass(frozen=True)
class Location:
    """The location in use: its path relative to the project root, and whether the
    configuration records it or it is the default, not recorded yet."""

    path: str
    recorded: bool

    def folder(self, root: Path) -> Path:
        return root / self.path


def configured(root: Path) -> str | None:
    """The location the configuration records, or None. Raises LocationRefused when the
    configuration cannot be read, records a location the rules refuse, or holds the key with
    no value."""
    target = root / CONFIG
    if not target.is_file():
        return None
    try:
        data = read_yaml(target)
    except ReadError as exc:
        raise LocationRefused(f"{CONFIG} cannot be read: {exc}") from exc
    if data is None:
        return None
    if not isinstance(data, dict):
        raise LocationRefused(f"{CONFIG} is not a mapping")
    if KEY not in data:
        return None
    value = data[KEY]
    if value is None:
        raise LocationRefused(
            f"{CONFIG} records an empty `{KEY}:`: write the folder that holds the ideas there, "
            f"such as `{KEY}: {DEFAULT}`, or remove the line"
        )
    if not isinstance(value, str):
        raise LocationRefused(f"{CONFIG} records `{KEY}: {value!r}`, which is not a path")
    found = problem(root, value)
    if found is not None:
        raise LocationRefused(f"{CONFIG} records the location `{value}`, which {found}")
    return value


def shape_problem(rel: str) -> str | None:
    """Why the repository-relative path `rel` cannot be the location, read from its text
    alone, or None."""
    if rel in ("", "."):
        return "is the repository's top itself: name a folder within it"
    if "\\" in rel:
        return "holds a `\\`: write the path with `/`"
    if PurePosixPath(rel).is_absolute():
        return "is absolute: give a path relative to the repository's top"
    parts = rel.split("/")
    if any(part == "" for part in parts):
        return "has an empty segment, such as a trailing or a doubled `/`"
    if ".." in parts:
        return "lies outside the repository"
    if parts[0] == ".pkit":
        return "lies under `.pkit/`, the methodology's own folder"
    if any(part.startswith(".") for part in parts):
        return "lies under a hidden folder"
    return None


def problem(root: Path, rel: str) -> str | None:
    """Why `rel` cannot be the location, from its text and from what lies there, or None. A
    folder that does not exist yet is no problem."""
    found = shape_problem(rel)
    if found is not None:
        return found
    target = root / rel
    for path in (target, *target.parents):
        if path == root:
            break
        if path.is_symlink():
            return f"is reached through the link {path.relative_to(root).as_posix()}"
    if target.exists() and not target.is_dir():
        return "is not a folder"
    return None


def for_reading(root: Path) -> Location | None:
    """The location the check and the reading commands read: the recorded one, else the
    default; None where nothing is recorded and the rules refuse the default as it lies, such
    as a file of that name. Raises LocationRefused when the configuration cannot be read or
    records a location the rules refuse."""
    recorded = configured(root)
    if recorded is not None:
        return Location(recorded, recorded=True)
    if problem(root, DEFAULT) is not None:
        return None
    return Location(DEFAULT, recorded=False)
