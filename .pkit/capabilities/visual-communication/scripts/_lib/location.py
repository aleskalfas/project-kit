"""The capability's location: the working folder that holds a project's libraries and
pieces (DEC-002 points 1 and 2).

- **Its default** is `visual/` at the repository's top. The configuration's `location:`
  records it, once a command first writes there (COR-049 point 5), so a later change of the
  default moves no recorded location.
- **A folder holds the capability's work** when it holds the list of libraries,
  `libraries/libraries.yaml`, or any YAML file bound to one of the capability's schemas:
  the *marker*.
- **A command that writes in the location** reads `location:`. Absent, it takes `visual/`
  and records it before its first write, where `visual/` is absent, empty, or holds the
  marker. Elsewhere it refuses, naming the folder, and asks for `--location <path>`, which
  it records; `--location visual` confirms the default.
- **The check and the commands that only read** take the recorded location, else `visual/`
  only where it holds the marker; with neither there is no visual work. A recorded location
  whose folder is missing fails, naming the configuration.
- **Refused:** the repository's top itself, a path outside the repository, under `.pkit/`,
  under a hidden folder, reached through a link, or not a folder. An empty `location:` is
  refused too, by reading and writing commands alike, rather than read as no location.

The files of a folder are listed as git sees them: tracked, and untracked but not ignored.
Outside a git repository, the folder is walked. A link is listed only where a caller asks
for links too (`listed`), as the reading of a picture file does, to tell a name that finds a
link from one that finds nothing. What a commit holds is read from git alone (`files_at`,
`file_at`). Whether a path is one git keeps is git's word too (`ignored`), and so is whether
git hands it to a large-file store (`in_store`).
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from _lib import config_text
from _lib.files import Change, is_of_format
from _lib.reading import ReadError, read_yaml
from _lib.root import CONFIG

#: The location's default, at the repository's top.
DEFAULT = "visual"

#: The configuration's key that records the location.
KEY = "location"

#: The list of the project's libraries, within the location (DEC-003 point 4).
LIBRARY_LIST = "libraries/libraries.yaml"


class LocationRefused(Exception):
    """No location can be used: one refused, or a configuration that cannot be read."""


class GitFailed(Exception):
    """Git could not list the files of a repository."""


@dataclass(frozen=True)
class Location:
    """The location in use: its path relative to the project root, and whether the
    configuration records it."""

    path: str
    recorded: bool

    def folder(self, root: Path) -> Path:
        return root / self.path


@dataclass(frozen=True)
class ForWriting:
    """The location a writing command uses, and whether it records it before its first
    write."""

    path: str
    record: bool


# --- the location -------------------------------------------------------------------------------


def configured(root: Path) -> str | None:
    """The location the configuration records, or None. Raises LocationRefused when the
    configuration cannot be read, records a location the rules refuse, or holds the key
    with no value."""
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
        raise LocationRefused(f"{CONFIG} is not a mapping; fix it first")
    if KEY not in data:
        return None
    value = data[KEY]
    if value is None:
        raise LocationRefused(
            f"{CONFIG} records an empty `{KEY}:`: write the folder that holds the work there, "
            f"such as `{KEY}: {DEFAULT}`, or remove the line"
        )
    if not isinstance(value, str):
        raise LocationRefused(f"{CONFIG} records `{KEY}: {value!r}`, which is not a path")
    problem = shape_problem(value)
    if problem is not None:
        raise LocationRefused(f"{CONFIG} records the location `{value}`, which {problem}")
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
    """Why `rel` cannot be the location, from its text and from what lies there, or
    None. A folder that does not exist yet is no problem."""
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


def normalise(root: Path, given: str, cwd: Path | None = None) -> str:
    """The location a person gives on the command line, `--location <path>`, relative to
    the working directory or absolute, as a path relative to the repository's top. Raises
    LocationRefused when the rules refuse it."""
    base = cwd if cwd is not None else Path.cwd()
    absolute = Path(os.path.normpath(Path(given) if Path(given).is_absolute() else base / given))
    try:
        rel = absolute.relative_to(Path(os.path.normpath(root))).as_posix()
    except ValueError:
        raise LocationRefused(f"the location `{given}` lies outside the repository") from None
    found = problem(root, rel)
    if found is not None:
        raise LocationRefused(f"the location `{given}` {found}")
    return rel


def for_reading(root: Path) -> Location | None:
    """The location the check and the reading commands use: the recorded one, else the
    default where it holds the marker; None when there is no visual work. Raises
    LocationRefused when the recorded location's folder is refused or missing."""
    recorded = configured(root)
    if recorded is not None:
        found = problem(root, recorded)
        if found is None and not (root / recorded).is_dir():
            found = "does not exist"
        if found is not None:
            raise LocationRefused(
                f"{CONFIG} records the location `{recorded}`, which {found}: restore the "
                f"folder, or change the `{KEY}:` line to where the work lies"
            )
        return Location(recorded, recorded=True)
    if (root / DEFAULT).is_dir() and problem(root, DEFAULT) is None and holds_marker(root, DEFAULT):
        return Location(DEFAULT, recorded=False)
    return None


def for_writing(root: Path, given: str | None = None, cwd: Path | None = None) -> ForWriting:
    """The location a writing command uses, `given` being its `--location` when a person
    gave one; and whether the command records it before its first write. Raises
    LocationRefused, naming the folder and the way out."""
    recorded = configured(root)
    if recorded is not None:
        if given is not None and normalise(root, given, cwd) != recorded:
            raise LocationRefused(
                f"{CONFIG} records the location `{recorded}`; a command never moves it. To "
                f"move the work, move the folder and change the `{KEY}:` line"
            )
        if not (root / recorded).is_dir():
            raise LocationRefused(
                f"{CONFIG} records the location `{recorded}`, which does not exist: restore "
                f"the folder, or change the `{KEY}:` line to where the work lies"
            )
        return ForWriting(recorded, record=False)
    if given is not None:
        return ForWriting(normalise(root, given, cwd), record=True)
    found = problem(root, DEFAULT)
    if found is not None:
        raise LocationRefused(
            f"the default location `{DEFAULT}` {found}: name the location with `--location <path>`"
        )
    if not (root / DEFAULT).exists() or not files(root, DEFAULT) or holds_marker(root, DEFAULT):
        return ForWriting(DEFAULT, record=True)
    raise LocationRefused(
        f"`{DEFAULT}/` holds files that are not the capability's work, so the command takes "
        f"no location there: name the location with `--location <path>`, or confirm the "
        f"default with `--location {DEFAULT}`"
    )


def record(change: Change, where: ForWriting) -> str | None:
    """Add to `change`, as its next step, the write that records the location `where`
    names in the configuration, every other byte kept, where the command records it; and
    return what the command says once the change is taken, naming where to change it
    (COR-049 point 5), or None. Writes nothing, so a command learns before its first write
    that it cannot record the location. Raises LocationRefused."""
    if not where.record:
        return None
    try:
        text = config_text.recording(change.root, KEY, where.path)
    except config_text.ConfigRefused as exc:
        raise LocationRefused(str(exc)) from exc
    if text is None:
        return None
    change.write(change.root / CONFIG, text.encode("utf-8"))
    origin = " (the default, at the repository's top)" if where.path == DEFAULT else ""
    return (
        f"recorded the location `{where.path}`{origin} in {CONFIG}; to move the work, move "
        f"the folder and change the `{KEY}:` line there"
    )


# --- what a folder holds ------------------------------------------------------------------------


def holds_marker(root: Path, folder: str) -> bool:
    """Whether `folder` holds the capability's work: the list of libraries, or a YAML file
    bound to one of the capability's schemas."""
    listed = files(root, folder)
    if f"{folder}/{LIBRARY_LIST}" in listed:
        return True
    for rel in listed:
        if not rel.endswith(".yaml"):
            continue
        try:
            if is_of_format(read_yaml(root / rel)):
                return True
        except ReadError:
            continue
    return False


def files(root: Path, folder: str) -> list[str]:
    """The files under `folder`, relative to `root`, as git sees them: tracked, and
    untracked but not ignored; walked outside a git repository. In path order, without
    links, and without a tracked file the working tree no longer holds."""
    return [rel for rel in listed(root, folder) if not (root / rel).is_symlink()]


def listed(root: Path, folder: str) -> list[str]:
    """The files under `folder` that `files` lists, and each link among them that git lists,
    or that lies there outside a git repository. In path order."""
    if not _in_repository(root):
        return walked(root, folder, links=True)
    found = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", folder)
    entries = {entry for entry in found.decode("utf-8").split("\0") if entry}
    return sorted(rel for rel in entries if _plain_file(root / rel) or (root / rel).is_symlink())


def files_at(root: Path, commit: str, folder: str) -> list[str]:
    """The files under `folder` at `commit`, relative to `root`, in path order: none where
    that commit holds no such folder. Raises GitFailed."""
    found = _git(root, "ls-tree", "-r", "-z", "--name-only", commit, "--", folder)
    return sorted(entry for entry in found.decode("utf-8").split("\0") if entry)


def file_at(root: Path, commit: str, rel: str) -> bytes:
    """The bytes of the file `rel`, relative to `root`, at `commit`. Raises GitFailed where
    that commit holds no such file."""
    return _git(root, "cat-file", "blob", f"{commit}:./{rel}")


def ignored(root: Path, paths: Iterable[str]) -> list[str]:
    """Those of `paths`, relative to `root`, that git ignores, whether or not a file lies
    there, so a commit would leave a file written there out: a tracked file is not one, and
    outside a git repository none is. Raises GitFailed."""
    if not _in_repository(root):
        return []
    asked = "\0".join(paths).encode("utf-8")
    found = _git(root, "check-ignore", "-z", "--stdin", literal=False, given=asked, passes=(0, 1))
    return [entry for entry in found.decode("utf-8").split("\0") if entry]


def in_store(root: Path, paths: Iterable[str]) -> list[str]:
    """Those of `paths`, relative to `root`, that git hands to a large-file store, by the
    attribute `filter=lfs`, so a commit holds the store's pointer in their place, not their
    bytes: none outside a git repository. Raises GitFailed."""
    asked = list(paths)
    if not asked or not _in_repository(root):
        return []
    given = "\0".join(asked).encode("utf-8")
    found = _git(root, "check-attr", "-z", "--stdin", "filter", literal=False, given=given)
    words = found.decode("utf-8").split("\0")
    # Each answer is three words: the path, the attribute's name and its value.
    return [words[i] for i in range(0, len(words) - 2, 3) if words[i + 2] == "lfs"]


def _git(
    root: Path,
    *args: str,
    literal: bool = True,
    given: bytes | None = None,
    passes: Collection[int] = (0,),
) -> bytes:
    """What git prints of `args`, run at `root`, handed `given` on its input: a path read as
    it is written, unless the command takes no such word (`literal`). Raises GitFailed where
    it exits with no code of `passes`."""
    words = ["--literal-pathspecs"] if literal else []
    try:
        proc = subprocess.run(
            ["git", *words, *args], cwd=root, input=given, capture_output=True, check=False
        )
    except OSError as exc:
        raise GitFailed(f"git could not be run ({exc})") from exc
    if proc.returncode not in passes:
        detail = [line for line in proc.stderr.decode("utf-8", "replace").splitlines() if line]
        raise GitFailed(detail[-1] if detail else f"git {args[0]} exited {proc.returncode}")
    return proc.stdout


def _in_repository(root: Path) -> bool:
    return any((folder / ".git").exists() for folder in (root, *root.parents))


def _plain_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def walked(root: Path, folder: str, *, links: bool = False) -> list[str]:
    """The files under `folder`, relative to `root`, as they lie, whatever git ignores: in
    path order, without links, unless `links` asks for each link too. A linked folder is
    never entered."""
    top = root / folder
    if not top.is_dir() or top.is_symlink():
        return []
    found = []
    for current, dirs, names in os.walk(top, followlinks=False):
        linked = [d for d in dirs if (Path(current) / d).is_symlink()]
        dirs[:] = [d for d in dirs if d not in linked]
        for name in (*names, *(linked if links else ())):
            path = Path(current) / name
            if _plain_file(path) or (links and path.is_symlink()):
                found.append(path.relative_to(root).as_posix())
    return sorted(found)
