"""Where a captured source is kept, and which file a source's name answers (DEC-001 point 4).

A page anchors a source outside the repository by its name (`source:
[keep-a-changelog]`), and each source is captured in one file of this
capability's project tier, found from the name alone:
`.pkit/capabilities/living-docs/project/sources/<name>.yaml`. This module is
the one home of that layout. The `source` resolver answers through `answer`,
and the validator reads every entry of the folder through `entries`, so the
two never disagree about what a name denotes.

The answer is the same on every machine (COR-050 point 2): every segment of
the folder must be a real folder, never a link; the file is matched by its
exact name, so a case-insensitive disk never finds `Keep.yaml` for `keep`;
and only a regular file answers, never a link or a folder. A name outside the
grammar, or one no such file captures, answers no file — the anchor is dead.
Only a failure to read the disk — a permission or I/O error — is no answer
(`Unreadable`).

Standard library only: the resolver has no dependencies to provision.
"""

from __future__ import annotations

import os
import re
import stat
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


class Unreadable(Exception):
    """The disk could not be read where sources are kept: no answer, never `[]`."""


@dataclass(frozen=True)
class Entry:
    """One entry of the sources folder, or the folder itself when it is not one.

    `name` is the source it captures, when it is a captured source; `problem`
    says why it is not one, otherwise."""

    path: str  # repository-relative
    name: str | None = None
    problem: str | None = None


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
    folder = root
    try:
        for part in FOLDER:  # every segment a real folder, never a link
            folder = folder / part
            if not stat.S_ISDIR(os.lstat(folder).st_mode):
                return []
        wanted = value + SUFFIX
        with os.scandir(folder) as found:  # the exact name, on any disk
            for entry in found:
                if entry.name == wanted:
                    return [file_path(value)] if entry.is_file(follow_symlinks=False) else []
    except (FileNotFoundError, NotADirectoryError):
        return []
    except OSError as exc:
        raise Unreadable(f"{folder}: {exc.strerror or exc}") from exc
    return []


def entries(root: Path) -> list[Entry]:
    """Every entry of the sources folder in the project at `root`, by name, each a
    captured source or saying why it is not one; the first segment of the folder's
    path that is not a real folder, alone, when there is one; none when the folder
    is not there. Raises Unreadable on an OSError other than a missing path."""
    folder = root
    rel: list[str] = []
    try:
        for part in FOLDER:
            folder = folder / part
            rel.append(part)
            if not stat.S_ISDIR(os.lstat(folder).st_mode):
                return [Entry("/".join(rel), problem=_not_a_folder(folder))]
        with os.scandir(folder) as found:
            listed = sorted(found, key=lambda entry: entry.name)
        return [_entry(entry) for entry in listed]
    except (FileNotFoundError, NotADirectoryError):
        return []
    except OSError as exc:
        raise Unreadable(f"{folder}: {exc.strerror or exc}") from exc


def _not_a_folder(path: Path) -> str:
    kind = "a link" if os.path.islink(path) else "not a folder"
    return f"is {kind}, so no source is read from it: every name answers no file"


def _entry(entry: os.DirEntry[str]) -> Entry:
    path = f"{folder_path()}/{entry.name}"
    if entry.is_symlink():
        return Entry(path, problem="is a link; a captured source is a regular file")
    if entry.is_dir(follow_symlinks=False):
        return Entry(path, problem="is a folder; a captured source is a regular file")
    if not entry.is_file(follow_symlinks=False):
        return Entry(path, problem="is not a regular file")
    stem = entry.name[: -len(SUFFIX)] if entry.name.endswith(SUFFIX) else None
    if stem is None or not is_name(stem):
        return Entry(path, problem=f"is not named `<name>{SUFFIX}` with a name of {GRAMMAR}")
    return Entry(path, name=stem)
