"""How the capability's scripts reach the backbone: `pkit`, through one function.

A capability script runs in its own environment and never imports the backbone (ADR-057
point 1). It reaches the backbone only through `pkit`'s commands, an argument list in and
one JSON document out. Every `pkit` call the capability makes goes through `run`, which
hands it to `_run`, looked up when called, so the calls have one start. A test answers
every call in its own process by replacing `_run` alone, the argument lists and the
documents unchanged.

Standard library only, so every command can import it, whatever it depends on.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from typing import Any


def run(argv: Sequence[str], **options: Any) -> subprocess.CompletedProcess[Any]:
    """Run `pkit` with `argv`, its first word `pkit`, and `subprocess.run`'s `options`."""
    return _run(argv, **options)


def _run(argv: Sequence[str], **options: Any) -> subprocess.CompletedProcess[Any]:
    """The one start of a `pkit` process: every call the capability makes comes here."""
    return subprocess.run(argv, **options)
