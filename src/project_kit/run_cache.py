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
removed when the run ends. With no directory named — `pkit connections
resolve` run from a shell, `pkit status` — nothing is read or written. Members
only read the tree, so an entry cannot go stale within a run. An entry that
cannot be read is a miss, never an error; one whose value JSON cannot hold is
never written.
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

# The environment variable naming the directory of the run in progress.
CACHE_ENV = "PKIT_RUN_CACHE"


@contextlib.contextmanager
def opened() -> Generator[None]:
    """The cache of one run: a fresh directory named in the environment for the
    length of the block, then removed. Inside a run that already names one — a
    `pkit validate` a command of another run started — that one, left in place."""
    if os.environ.get(CACHE_ENV):
        yield
        return
    directory = tempfile.mkdtemp(prefix="pkit-run-")
    os.environ[CACHE_ENV] = directory
    try:
        yield
    finally:
        os.environ.pop(CACHE_ENV, None)
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
    if not directory:
        return None
    return Path(directory) / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"
