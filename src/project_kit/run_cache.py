"""The run cache: what one run of `pkit validate` computed, shared with the
`pkit` commands the run starts (ADR-057 point 2).

Within one process, `validators.once_per_run` makes each shared computation
once. A capability's validator runs in a process of its own and reads what the
backbone computes through the backbone's reading commands — a data point
through `pkit connections resolve --json` — so without more it would compute
it again, a point's command fillers started a second time. The run cache
carries a computation across: `pkit validate` opens it for the length of its
run (`opened`) and names its directory in the environment (`CACHE_ENV`), which
every command the run starts inherits, and those commands' own `pkit`
commands after them; whatever computes a value the cache keeps writes it there
(`write`), and a reader in any of those processes reads it (`read`) before
computing it itself. The data points' resolution keeps each resolved point
here, keyed by the project root and the point's address (`data_points`).

The directory is the run's alone — a fresh temporary directory — and is
removed when the run ends. Only a process of the run uses it: the one that
opened it, or one running inside a live run
(`command_runner.inherited_deadline`), as every command the run starts is. A
directory named in the environment of any other process — a variable left over
in a shell, or outliving its run — is ignored: nothing is read from it or
written to it, and `opened` makes a fresh one. With no directory — `pkit
connections resolve` run from a shell, `pkit status`, or a run that could not
make one — nothing is read or written, and every reader computes for itself.
Members only read the tree, so an entry cannot go stale within a run. An entry
that cannot be read is a miss, never an error; one whose value JSON cannot hold
is never written.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

from project_kit import command_runner

# The environment variable naming the directory of the run in progress — the
# runner's own, never read or set by a command.
CACHE_ENV = "PKIT_RUN_CACHE"

# The directory this process opened, while its run lasts.
_opened: str | None = None


@contextlib.contextmanager
def opened() -> Generator[None]:
    """The cache of one run: a fresh directory named in the environment for the
    length of the block, then removed. Inside a live run that already names one
    — a `pkit validate` a command of another run started — that one, left in
    place. When no directory can be made, the run goes without a cache."""
    global _opened
    named = os.environ.get(CACHE_ENV)
    if named and _usable(named):
        yield
        return
    try:
        directory: str | None = tempfile.mkdtemp(prefix="pkit-run-")
    except OSError:
        directory = None
    outer = _opened
    _name(directory)
    _opened = directory
    try:
        yield
    finally:
        _opened = outer
        _name(named)
        if directory is not None:
            shutil.rmtree(directory, ignore_errors=True)


def read(key: str) -> Any | None:
    """The value the run holds for `key`, or None: no run named, nothing held,
    or an entry that cannot be read."""
    path = _entry(key)
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write(key: str, value: Any) -> None:
    """Keep `value` for `key` for the rest of the run — whole or not at all, so a
    reader never sees half an entry. Outside a run, or for a value JSON cannot
    hold, nothing is kept."""
    path = _entry(key)
    if path is None:
        return
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return
    with contextlib.suppress(OSError):  # a cache that cannot be written only costs a recomputation
        handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)


def _entry(key: str) -> Path | None:
    """Where the run keeps `key`, or None outside a run."""
    directory = os.environ.get(CACHE_ENV)
    if not directory or not _usable(directory):
        return None
    return Path(directory) / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"


def _usable(directory: str) -> bool:
    """Whether this process belongs to the run whose cache `directory` is: it
    opened it, or it runs inside a live run, which only a process the opening
    run started does."""
    return directory == _opened or command_runner.inherited_deadline() is not None


def _name(directory: str | None) -> None:
    """Name `directory` in the environment the run's commands inherit, or none."""
    if directory is None:
        os.environ.pop(CACHE_ENV, None)
    else:
        os.environ[CACHE_ENV] = directory
