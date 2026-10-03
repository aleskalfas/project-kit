"""Where a captured source is kept, and which file a source's name answers (DEC-001 point 4).

A page anchors a source outside the repository by its name (`source:
[keep-a-changelog]`), and each source is captured in one file of this
capability's project tier, found from the name alone:
`.pkit/capabilities/living-docs/project/sources/<name>.yaml`. This module is
the one home of that layout. The `source` resolver answers through `answer`,
and the validator reads every entry of the folder through `entries`, so the
two never disagree about what a name denotes.

The answer is the same on every machine (COR-050 point 2): every segment of
the folder's path, and then the file, is found by its exact name in a listing
of its parent, so a case-insensitive disk never finds `Sources/` for
`sources` or `Keep.yaml` for `keep`; every segment must be a real folder,
never a link; and only a regular file answers, never a link or a folder. A
name outside the grammar, or one no such file captures, answers no file — the
anchor is dead. Only a failure to read the disk — a permission or I/O error —
is no answer (`Unreadable`).

An entry of the folder whose name begins with `.` — `.gitkeep`, an editor's
or a desktop's file — is never a captured source and never listed: no
source's name begins with one, so it can answer no name.

Standard library only: the resolver has no dependencies to provision.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from _lib.root import CAPABILITIES_DIR, CAPABILITY

#: The folder captured sources are kept in, segment by segment from the project root.
FOLDER: tuple[str, ...] = (*CAPABILITIES_DIR.split("/"), CAPABILITY, "project", "sources")

#: A captured source's file is its name and this suffix.
SUFFIX = ".yaml"

#: A source's name: lower-case words of letters and digits joined by single
#: hyphens, starting with a letter (matched whole), at most `NAME_LIMIT` long.
NAME = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*")
NAME_LIMIT = 64

#: The grammar in words, for a message.
GRAMMAR = (
    "lower-case words of letters and digits joined by single hyphens, starting with a "
    f"letter, at most {NAME_LIMIT} characters"
)

#: What a segment of the folder's path that is not the folder it names leaves.
_READS_NONE = "no source is read from it: every name answers no file"


class Unreadable(Exception):
    """The disk could not be read where sources are kept: no answer, never `[]`."""


@dataclass(frozen=True)
class Entry:
    """One entry of the sources folder, or a segment of the folder's path when it
    is not the folder it names.

    `name` is the source it captures, when it is a captured source; `problem`
    says why it is not one, otherwise, and `error` whether that fails
    validation: everything but a regular file whose name does not end in
    `SUFFIX` — notes, an editor's backup — which is only reported."""

    path: str  # repository-relative
    name: str | None = None
    problem: str | None = None
    error: bool = True


def folder_path() -> str:
    """The sources folder, repository-relative."""
    return "/".join(FOLDER)


def file_path(value: str) -> str:
    """The file that would capture the source `value`, repository-relative."""
    return f"{folder_path()}/{value}{SUFFIX}"


def is_name(value: str) -> bool:
    """Whether `value` is a source's name by the grammar."""
    return len(value) <= NAME_LIMIT and NAME.fullmatch(value) is not None


def answer(root: Path, value: str) -> list[str]:
    """The file capturing the source `value` in the project at `root`, as a list of
    one repository-relative path; `[]` when the value is outside the grammar, or no
    regular file captures it. Raises Unreadable on any other OSError (no answer)."""
    if not is_name(value):
        return []
    wanted = value + SUFFIX
    try:
        folder = _reach(root)
        if not isinstance(folder, Path):
            return []
        found = _alike(folder, wanted).get(wanted)
        if found is None or not found.is_file(follow_symlinks=False):
            return []
        return [file_path(value)]
    except (FileNotFoundError, NotADirectoryError):
        return []
    except OSError as exc:
        raise _unreadable(root, exc) from exc


def entries(root: Path) -> list[Entry]:
    """Every entry of the sources folder in the project at `root` but the hidden
    ones, by name, each a captured source or saying why it is not one; the first
    segment of the folder's path that is not the folder it names, alone, when
    there is one; none when the folder is not there. Raises Unreadable on an
    OSError other than a missing path."""
    try:
        folder = _reach(root)
        if not isinstance(folder, Path):
            return [] if folder is None else [folder]
        with os.scandir(folder) as found:
            listed = sorted(found, key=lambda entry: entry.name)
        return [_entry(entry) for entry in listed if not entry.name.startswith(".")]
    except (FileNotFoundError, NotADirectoryError):
        return []
    except OSError as exc:
        raise _unreadable(root, exc) from exc


def _reach(root: Path) -> Path | Entry | None:
    """The sources folder in the project at `root`, each segment of its path found
    by its exact name in a listing of its parent, and each a real folder. Instead,
    the first segment that is not: an Entry naming a file or a link there, or a
    name that differs from the segment's only in case; or None when there is
    nothing of the segment's name in any case. Raises OSError when a folder on the
    path cannot be listed."""
    folder = root
    for depth, part in enumerate(FOLDER):
        alike = _alike(folder, part)
        found = alike.get(part)
        if found is None:
            if not alike:
                return None
            cased = "/".join((*FOLDER[:depth], min(alike)))
            return Entry(cased, problem=f"differs from `{part}` only in case, so {_READS_NONE}")
        if found.is_symlink() or not found.is_dir(follow_symlinks=False):
            kind = "a link" if found.is_symlink() else "not a folder"
            return Entry("/".join(FOLDER[: depth + 1]), problem=f"is {kind}, so {_READS_NONE}")
        folder = folder / part
    return folder


def _alike(folder: Path, name: str) -> dict[str, os.DirEntry[str]]:
    """The entries of `folder` whose names equal `name` in any case, by their exact
    names. A listing gives each name exactly on any disk, where looking a path up
    ignores case on a case-insensitive one."""
    folded = name.casefold()
    with os.scandir(folder) as listed:
        return {entry.name: entry for entry in listed if entry.name.casefold() == folded}


def _unreadable(root: Path, exc: OSError) -> Unreadable:
    where = exc.filename if exc.filename is not None else root
    return Unreadable(f"{where}: {exc.strerror or exc}")


def _entry(entry: os.DirEntry[str]) -> Entry:
    path = f"{folder_path()}/{entry.name}"
    if entry.is_symlink():
        return Entry(path, problem="is a link; a captured source is a regular file")
    if entry.is_dir(follow_symlinks=False):
        return Entry(path, problem="is a folder; a captured source is a regular file")
    if not entry.is_file(follow_symlinks=False):
        return Entry(path, problem="is not a regular file")
    if not entry.name.endswith(SUFFIX):
        return Entry(path, problem=f"does not end in `{SUFFIX}`", error=False)
    stem = entry.name[: -len(SUFFIX)]
    if not is_name(stem):
        return Entry(path, problem=f"is not named `<name>{SUFFIX}` with a name of {GRAMMAR}")
    return Entry(path, name=stem)
