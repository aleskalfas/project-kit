"""A file of the capability's format: its binding, its shape, the nearest known key, and
writing one whole (DEC-002 points 3 and 4, DEC-003 point 1).

Each file of the format names its schema and the format number at its top, in the fields
by which the core binds a data file: `pkit_schema: visual-communication:<kind>` and
`schema_version: 1`. No path binds one. The core's data validation checks a bound file's
shape against its schema; the capability's check fails a file of the format whose binding
is missing or names another schema, and names the nearest known key where content holds
one no component declares.

A command writes the files of one run as one `Change`: where a write fails, every file is
put back as it was before the run, or named in the `WriteFailed` it raises.
"""

from __future__ import annotations

import contextlib
import difflib
import os
import shutil
import stat
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from _lib.reading import read_yaml
from _lib.root import CAPABILITY, SHIPPED

#: The format number, shared by every schema of the capability (DEC-003 point 1).
FORMAT = 1

#: The capability's schemas, one pair for each kind of file.
SCHEMAS = SHIPPED / "schemas"

#: The kinds of file of format 1, each a schema of the capability.
KINDS = (
    "config",
    "piece",
    "content",
    "library",
    "component",
    "roles",
    "notation",
    "libraries",
    "produced-record",
    "code-record",
    "findings",
    "exports",
    "code",
)

SCHEMA_FIELD = "pkit_schema"
VERSION_FIELD = "schema_version"


class FileError(Exception):
    """A file of the format the capability cannot read as the kind asked for."""


def schema_of(kind: str) -> str:
    """The value of `pkit_schema` that binds a file of `kind`."""
    return f"{CAPABILITY}:{kind}"


def is_of_format(data: Any) -> bool:
    """Whether `data` names one of the capability's schemas, at whatever number."""
    return (
        isinstance(data, Mapping)
        and isinstance(data.get(SCHEMA_FIELD), str)
        and data[SCHEMA_FIELD].startswith(f"{CAPABILITY}:")
    )


def binding_problem(data: Any, kind: str) -> str | None:
    """Why `data` is not a file of `kind` at format 1, or None."""
    wanted = schema_of(kind)
    fix = f"`{SCHEMA_FIELD}: {wanted}` and `{VERSION_FIELD}: {FORMAT}` at its top"
    if not isinstance(data, Mapping):
        return f"is not a mapping, so it names no schema: write {fix}"
    named = data.get(SCHEMA_FIELD)
    if named is None:
        return f"names no schema: add {fix}"
    if named != wanted:
        return f"names the schema `{named}`, not `{wanted}`"
    number = data.get(VERSION_FIELD)
    if number is None:
        return f"names no format number: add `{VERSION_FIELD}: {FORMAT}`"
    if isinstance(number, bool) or number != FORMAT:
        return f"is at format {number!r}; the installed capability reads format {FORMAT}"
    return None


def without_binding(data: Mapping[str, Any]) -> dict[str, Any]:
    """`data` with the fields that bind it removed."""
    return {key: value for key, value in data.items() if key not in (SCHEMA_FIELD, VERSION_FIELD)}


def read_bound(path: Path, kind: str) -> dict[str, Any]:
    """The value of the file of `kind` at `path`. Raises FileError when it cannot be read
    or is not bound to `kind` at format 1; ReadError from reading passes through."""
    data = read_yaml(path)
    problem = binding_problem(data, kind)
    if problem is not None:
        raise FileError(f"{path}: {problem}")
    return dict(data)


def nearest(key: str, known: Iterable[str]) -> str | None:
    """The known key nearest to `key`, where one is near enough to be a likely slip."""
    found = difflib.get_close_matches(key, sorted(known), n=1, cutoff=0.6)
    return found[0] if found else None


def unknown_keys(data: Mapping[str, Any], known: Iterable[str]) -> list[tuple[str, str | None]]:
    """Each key of `data` that `known` does not hold, with the nearest known key or None."""
    known = tuple(known)
    return [(key, nearest(key, known)) for key in data if key not in known]


def shape_problems(data: Any, kind: str) -> list[str]:
    """What the schema of `kind` refuses in `data`, each `<JSON pointer>: <message>`;
    empty when it holds. Needs `jsonschema`, imported only here."""
    import json

    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    resources = []
    for companion in sorted(SCHEMAS.glob("*.schema.json")):
        contents = json.loads(companion.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        resources.append((contents.get("$id", companion.name), resource))
    registry = Registry().with_resources(resources)
    schema = json.loads((SCHEMAS / f"{kind}.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, registry=registry)
    problems = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path))):
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        problems.append(f"{pointer}: {error.message}")
    return problems


# --- writing ------------------------------------------------------------------------------------


def refuse_links(root: Path, target: Path) -> None:
    """Raise FileError when `target`, or a folder between it and `root`, is a link: a file
    written whole would replace the link it was reached by."""
    for path in (target, *target.parents):
        if path == root:
            return
        if path.is_symlink():
            raise FileError(
                f"{target.relative_to(root).as_posix()} is reached through the link "
                f"{path.relative_to(root).as_posix()}: put the file or folder itself in the "
                f"link's place"
            )


def write_whole(target: Path, data: bytes) -> None:
    """Write `data` to `target` whole or not at all: to a temporary file beside it, then
    moved over it. A file keeps its mode; a new one takes what the umask gives."""
    temporary = _beside(target, data)
    try:
        os.replace(temporary, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def _beside(target: Path, data: bytes) -> Path:
    """A temporary file beside `target` that holds `data`, on the disk, with the mode
    `target` has, or the umask gives a new file."""
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o666 & ~_umask()
    handle, name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise
    return temporary


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


# --- a change of several files ------------------------------------------------------------------


class WriteFailed(Exception):
    """A write that failed: the message names the file that could not be written, or
    removed, and why, and each file the command could not then put back as it was before
    the run."""

    def __init__(
        self,
        root: Path,
        path: Path,
        error: OSError,
        left: Sequence[Path] = (),
        *,
        done: str = "written",
    ) -> None:
        said = f"{_shown(root, path)} could not be {done}: {error.strerror or error}"
        if left:
            named = ", ".join(_shown(root, each) for each in left)
            said += f"; these could not be put back as they were before the run: {named}"
        super().__init__(said)
        self.path = path
        self.left = tuple(left)


class Change:
    """The files a command writes, folders it adds or replaces and files it removes, as one
    change: a write that fails leaves every file as it was before the run, or names each it
    could not put back.

    `commit` stages every step beside its place first: a file is written to a temporary
    file beside it, a folder is copied to a temporary folder beside it, and a file to remove
    is read. Then it moves each into place, or removes it, in the order the steps were
    given, so a command gives its records last. A folder it replaces is moved aside, beside
    its place, before its copy is moved in. Where a step fails, each step taken is taken
    back, the last first: a file the change made is removed, a file it replaced or removed
    is written again with its bytes from before, a folder it added is removed, and a folder
    it replaced is moved back. Every temporary file and folder is removed, and every folder
    the change made that is empty again. Once every step is taken, each folder moved aside
    is removed; one that cannot be stays beside its place, hidden, as a temporary file
    whose removal fails does."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._steps: list[_Step] = []
        self._made: list[Path] = []

    def write(self, target: Path, data: bytes) -> None:
        """Write `data` to the file `target`, whole, making its folders."""
        self._steps.append(_Write(target, data))

    def add_folder(self, target: Path, sources: Mapping[str, Path | bytes]) -> None:
        """Add the folder `target`, which does not exist, holding each file of `sources` at
        its path within the folder: a copy of the file a path names, or the bytes given."""
        self._steps.append(_Folder(target, sources))

    def replace_folder(self, target: Path, sources: Mapping[str, Path]) -> None:
        """Replace the folder `target`, which exists, whole, by a folder holding a copy of
        each file of `sources` at its path within the folder."""
        self._steps.append(_Replacement(target, sources))

    def remove(self, target: Path) -> None:
        """Remove the file `target`."""
        self._steps.append(_Removal(target))

    def commit(self) -> None:
        """Take every step, or none. Raises WriteFailed, naming the step that failed and
        each file it could not put back."""
        taken: list[_Step] = []
        step: _Step | None = None
        try:
            for step in self._steps:
                self._make_folders(step.target.parent)
                step.stage()
            for step in self._steps:
                step.take()
                taken.append(step)
        except OSError as exc:
            assert step is not None
            left = self._take_back(taken)
            raise WriteFailed(self.root, step.target, exc, left, done=step.done) from exc
        except BaseException:
            # An interrupt, or any other error, between two steps takes the run back too,
            # then goes on as it came.
            self._take_back(taken)
            raise
        for step in self._steps:
            step.finish()

    def _make_folders(self, folder: Path) -> None:
        """Make `folder`, and each folder above it that is missing, keeping each one made."""
        missing = []
        while not folder.exists() and folder != folder.parent:
            missing.append(folder)
            folder = folder.parent
        for each in reversed(missing):
            each.mkdir()
            self._made.append(each)

    def _take_back(self, taken: Sequence[_Step]) -> list[Path]:
        """Take back each step taken, the last first, and remove every temporary file and
        folder, then each folder made that is empty again; each path that could not be put
        back as it was."""
        left = []
        for step in reversed(taken):
            try:
                step.take_back()
            except OSError:
                left.append(step.target)
        for step in self._steps:
            try:
                step.discard()
            except OSError:
                left.append(step.staged or step.target)
        for folder in reversed(self._made):
            with contextlib.suppress(OSError):
                folder.rmdir()
        return left


class _Step:
    """One step of a change: staged beside its place, then taken, and taken back where a
    later step fails. `done` is the word for it in a failure."""

    done = "written"

    def __init__(self, target: Path) -> None:
        self.target = target
        self.staged: Path | None = None
        self.before: bytes | None = None

    def stage(self) -> None:
        raise NotImplementedError

    def take(self) -> None:
        raise NotImplementedError

    def take_back(self) -> None:
        raise NotImplementedError

    def discard(self) -> None:
        """Remove what was staged and not taken."""
        if self.staged is not None:
            self.staged.unlink(missing_ok=True)
            self.staged = None

    def finish(self) -> None:
        """Once every step is taken, remove what was kept to take this one back."""


class _Write(_Step):
    def __init__(self, target: Path, data: bytes) -> None:
        super().__init__(target)
        self.data = data

    def stage(self) -> None:
        self.before = self.target.read_bytes() if self.target.exists() else None
        self.staged = _beside(self.target, self.data)

    def take(self) -> None:
        assert self.staged is not None
        os.replace(self.staged, self.target)
        self.staged = None

    def take_back(self) -> None:
        if self.before is None:
            self.target.unlink(missing_ok=True)
        else:
            write_whole(self.target, self.before)


class _Folder(_Step):
    def __init__(self, target: Path, sources: Mapping[str, Path | bytes]) -> None:
        super().__init__(target)
        self.sources = sources

    def stage(self) -> None:
        self.staged = _free_folder(self.target, ".tmp")
        for rel, source in self.sources.items():
            copied = self.staged / rel
            copied.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(source, bytes):
                copied.write_bytes(source)
            else:
                shutil.copyfile(source, copied)

    def take(self) -> None:
        assert self.staged is not None
        os.rename(self.staged, self.target)
        self.staged = None

    def take_back(self) -> None:
        shutil.rmtree(self.target)

    def discard(self) -> None:
        if self.staged is not None:
            shutil.rmtree(self.staged)
            self.staged = None


class _Replacement(_Folder):
    """A folder replaced whole: its copy staged beside it, the folder moved aside, beside
    its place, and the copy moved in. Taken back, the copy is removed and the folder moved
    back; once every step is taken, the folder moved aside is removed."""

    done = "replaced"

    def __init__(self, target: Path, sources: Mapping[str, Path]) -> None:
        super().__init__(target, sources)
        self.aside: Path | None = None

    def take(self) -> None:
        assert self.staged is not None
        aside = _free_folder(self.target, ".old")
        aside.rmdir()
        os.rename(self.target, aside)
        self.aside = aside
        try:
            os.rename(self.staged, self.target)
        except BaseException:
            # Moved back at once; where that fails too, `discard` moves it back, or names it.
            with contextlib.suppress(OSError):
                os.rename(aside, self.target)
                self.aside = None
            raise
        self.staged = None

    def take_back(self) -> None:
        assert self.aside is not None
        shutil.rmtree(self.target)
        os.rename(self.aside, self.target)
        self.aside = None

    def discard(self) -> None:
        super().discard()
        if self.aside is not None and not self.target.exists():
            os.rename(self.aside, self.target)
            self.aside = None

    def finish(self) -> None:
        if self.aside is not None:
            with contextlib.suppress(OSError):
                shutil.rmtree(self.aside)
            self.aside = None


def _free_folder(target: Path, suffix: str) -> Path:
    """A new, empty folder beside `target`, hidden, under a name no other file has."""
    parent, name = target.parent, target.name
    return Path(tempfile.mkdtemp(dir=parent, prefix=f".{name}.", suffix=suffix))


class _Removal(_Step):
    done = "removed"

    def stage(self) -> None:
        self.before = self.target.read_bytes() if self.target.exists() else None

    def take(self) -> None:
        if self.before is not None:
            self.target.unlink()

    def take_back(self) -> None:
        if self.before is not None:
            write_whole(self.target, self.before)


def _shown(root: Path, path: Path) -> str:
    """`path` as a command names it: relative to the project root, where it lies within it."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
