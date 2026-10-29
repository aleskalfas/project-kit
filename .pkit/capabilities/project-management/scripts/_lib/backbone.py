"""How the capability's scripts reach the backbone: `pkit`, through one function.

A capability script runs in its own environment and never imports the backbone
(ADR-057 point 1). It reaches the backbone only through `pkit`'s commands, an
argument list in and, for a reading, one JSON document out (the lifecycle
README, "How a registered command is run"). Every `pkit` call the `_lib`
modules make with `subprocess.run`, each reading and each write, goes through
`run`, the default runner of every function there that calls `pkit`, or is made
through it directly. `run` hands the call to `_run`, looked up when called, so
those calls have one start. A test answers them in its own process by replacing
`_run` alone, the argument lists and the documents unchanged. Two starts do not
come here: `agent_runs` and `merge_queue` stream a `pkit` process with
`subprocess.Popen`, which `run`'s signature cannot carry. Nor does a call the
top-level scripts make, nor one that starts another program, such as `git`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from typing import Any


def run(argv: Sequence[str], **options: Any) -> subprocess.CompletedProcess[Any]:
    """Run `pkit` with `argv`, its first word `pkit`, and `subprocess.run`'s `options`."""
    return _run(argv, **options)


def _run(argv: Sequence[str], **options: Any) -> subprocess.CompletedProcess[Any]:
    """The one start of a `pkit` process that the `_lib` modules make through `run`."""
    return subprocess.run(argv, **options)
