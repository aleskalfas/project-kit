"""The queue of the fixers' proposals (DEC-056 point 6).

The drift command gathers each run's proposals into the agent workspace of the
repository's main working tree, in a folder of this capability's, so removing
a worktree removes no proposal. The landing command prints how many wait. This
module is where the queue lies and how it is read and written:

- `folder` is the queue's folder: `.agent-workspace/project-management/drift/`
  in the main working tree. A repository with no main working tree, a bare one,
  has no queue, and `folder` says why.
- `read_index` and `write_index` read and write `index.json`. An absent index is
  an empty queue. One that cannot be read, or holds another `schema_version`,
  raises Unreadable: nothing guesses at a queue. A write goes to a file beside
  the index first and then replaces it, so a reader never sees half of one.
- `lock` holds `drift.lock`, so one run at a time works on the queue. It never
  waits: a lock another run holds raises Held.
- `waiting` counts the artefacts that wait on the person, those `proposed` or
  `held` with a question not yet answered, and `count_line` is the landing
  command's line for them. The commands that show and decide them are
  `_lib/proposals.py`'s.

The index's shape (`schema_version` 1): `contract_version`, the version of the
run's contract its last write followed; `artefacts`, each artefact's entry with
its `state` among `STATES`; `refusals`, each refusal the person gave, against
the artefact's friction; and `runs`, each run with what each fixer did. Each
run's files lie under `runs/<run>/<agent>/`, and a breach's under
`set-aside/<run>/<agent>/`. The drift command writes the entries; this module
checks only what its readers rely on.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any

try:  # Only where the platform has file locks.
    import fcntl
except ImportError:  # pragma: no cover — no such module off POSIX
    fcntl = None  # type: ignore[assignment]

#: Where the queue lies in the main working tree: its agent workspace, then this
#: capability's folder there.
WORKSPACE = ".agent-workspace"
FOLDER = Path(WORKSPACE) / "project-management" / "drift"
INDEX = "index.json"
LOCK = "drift.lock"
RUNS = "runs"
SET_ASIDE = "set-aside"

#: The version of the index this module reads and writes.
SCHEMA_VERSION = 1

#: The states an artefact's entry takes, and those that wait on the person.
STATES = ("proposed", "held", "none", "failed", "set-aside")
WAITING = ("proposed", "held")

#: The command that gathers the queue, as the count line names it.
GATHERED_BY = "pkit pm fix-drift"

#: The index's top-level keys that map names to entries.
_MAPPINGS = ("artefacts", "refusals", "runs")

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Unreadable(Exception):
    """The queue's index cannot be read as one of this version."""


class Held(Exception):
    """Another run holds the queue's lock, or no lock can be taken here."""


# --- where the queue lies ----------------------------------------------------------------


def main_working_tree(cwd: Path | None = None, run: Runner = subprocess.run) -> Path | str:
    """The repository's main working tree, or why there is none: the folder that
    holds the repository's common git folder, unless the repository is bare."""
    common = _git(run, cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common is None:
        return "git cannot be run"
    if not isinstance(common, Path):
        return f"no git repository is here ({common})"
    bare = _git(run, cwd, "--git-dir", str(common), "rev-parse", "--is-bare-repository")
    if bare == "true":
        return f"the repository at {common} is bare, so it has no main working tree"
    if bare != "false":
        return f"whether the repository at {common} is bare cannot be read ({bare})"
    tree = common.parent
    if not tree.is_dir():
        return f"the main working tree {tree} is not there"
    return tree


def folder(cwd: Path | None = None, run: Runner = subprocess.run) -> Path | str:
    """The queue's folder in the main working tree, or why there is none. The folder
    need not exist yet."""
    tree = main_working_tree(cwd, run)
    if isinstance(tree, str):
        return f"no queue can be kept: {tree}"
    return tree / FOLDER


def _git(run: Runner, cwd: Path | None, *argv: str) -> Path | str | None:
    """`git <argv>`'s one line of output: a Path for an absolute path, the text
    otherwise, or why it failed as a text that is no path. None when git cannot
    be run."""
    try:
        proc = run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        said = (proc.stderr or "").strip().splitlines()
        return f"git exited {proc.returncode}" + (f": {said[-1]}" if said else "")
    out = (proc.stdout or "").strip()
    return Path(out) if out.startswith("/") else out


# --- the index -----------------------------------------------------------------------------


def empty_index() -> dict[str, Any]:
    """An empty queue's index. Its `contract_version` is None until a run writes it."""
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": None,
        "artefacts": {},
        "refusals": {},
        "runs": {},
    }


def read_index(queue: Path) -> dict[str, Any]:
    """The index in the queue's folder `queue`. Absent, it is empty. Raises
    Unreadable when it cannot be read, is not JSON, holds another
    `schema_version`, or an entry its readers rely on is off its shape."""
    path = queue / INDEX
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return empty_index()
    except (OSError, UnicodeDecodeError) as exc:
        raise Unreadable(f"{path} cannot be read: {exc}") from exc
    try:
        index = json.loads(text)
    except ValueError as exc:
        raise Unreadable(f"{path} is not JSON: {exc}") from exc
    _check(index, path)
    return index


def _check(index: Any, where: Path | str) -> None:
    """Raise Unreadable where `index` is not an index this module reads."""
    if not isinstance(index, dict):
        raise Unreadable(f"{where} is not an object")
    version = index.get("schema_version")
    if version != SCHEMA_VERSION:
        raise Unreadable(f"{where} is at schema_version {version!r}; this reads {SCHEMA_VERSION}")
    for key in _MAPPINGS:
        value = index.get(key, {})
        if not isinstance(value, dict) or not all(isinstance(v, dict) for v in value.values()):
            raise Unreadable(f"{where}: `{key}` does not map each name to an object")
    for name, entry in index.get("artefacts", {}).items():
        if entry.get("state") not in STATES:
            raise Unreadable(
                f"{where}: artefact {name!r} is in state {entry.get('state')!r}, not one of "
                f"{', '.join(STATES)}"
            )


def write_index(queue: Path, index: Mapping[str, Any]) -> None:
    """Write `index` into the queue's folder `queue`, making the folder where it is
    missing. It goes to a file beside the index first, which then replaces the
    index whole. Raises Unreadable, writing nothing, where `index` is not one this
    module would read back."""
    _check(dict(index), INDEX)
    queue.mkdir(parents=True, exist_ok=True)
    text = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    handle, temporary = tempfile.mkstemp(dir=queue, prefix=f".{INDEX}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, queue / INDEX)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


# --- the lock --------------------------------------------------------------------------------


@contextlib.contextmanager
def lock(queue: Path) -> Iterator[Path]:
    """Hold the queue's lock for one run, and yield the lock's file. Never waits:
    raises Held where another run holds it, or where this platform has no file
    lock. The lock is released when the block ends, or when the process does."""
    if fcntl is None:  # pragma: no cover — POSIX has fcntl
        raise Held("this platform has no file lock, so one run at a time cannot be held")
    queue.mkdir(parents=True, exist_ok=True)
    path = queue / LOCK
    handle = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            holder = _holder(path)
            raise Held(
                f"another run holds {path}" + (f" (process {holder})" if holder else "")
            ) from exc
        os.ftruncate(handle, 0)
        os.write(handle, f"{os.getpid()}\n".encode())
        try:
            yield path
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        os.close(handle)


def _holder(path: Path) -> str:
    """The process the lock's file names, as its holder wrote it, or ""."""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""
    return text if text.isdigit() else ""


# --- what waits ------------------------------------------------------------------------------


def waiting(index: Mapping[str, Any]) -> int:
    """How many artefacts wait on the person: those `proposed`, and those `held`
    with a question the person has not answered. An answered question waits for
    the next run, not for the person."""
    entries = index.get("artefacts") or {}
    return sum(
        1
        for entry in entries.values()
        if entry.get("state") in WAITING
        and not (entry.get("state") == "held" and entry.get("answer"))
    )


def count_line(count: int, queue: Path) -> str | None:
    """The landing command's line for `count` waiting artefacts, naming the queue's
    folder, or None when nothing waits."""
    if count <= 0:
        return None
    noun = "proposal waits" if count == 1 else "proposals wait"
    return f"fixers: {count} {noun} for you — {GATHERED_BY} gathered them in {queue}"
