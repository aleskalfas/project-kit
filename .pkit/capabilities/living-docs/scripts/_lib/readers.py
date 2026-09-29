"""The readers point, read as it resolves (DEC-001 point 7).

`pkit::documentation:readers` is a data point this capability defines as the
provider of the `pkit::documentation` role (COR-052, COR-053): who reads the
documentation. Its value is `union` — the default's `user` and `maintainer`,
always included, merged by id with any capability's readers and the project's
filler file — and its inert policy is `fail`, so a filler that cannot answer
leaves the whole point unresolved.

A capability script runs in its own environment and never imports the backbone,
so the point is read through the backbone's read command, `pkit connections
resolve <point> --json` (the lifecycle README, "Reading one point from a
script"). The command exits 1 on an unresolved point and still prints its
document, so the document decides, never the exit code.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

#: The point, and where a project's own filler file for it lives, under the
#: internal documentation root (the lifecycle README, "Where a project filler
#: file lives").
READERS_POINT = "pkit::documentation:readers"
FILLER_SUBPATH = "pkit/fillers/pkit/documentation/readers.yaml"

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Readers:
    """The readers point as it resolved: the reader ids, or why there are none."""

    resolved: bool
    ids: tuple[str, ...] = ()  # sorted
    why: str = ""  # when unresolved


def read_readers(run: Runner = subprocess.run) -> Readers:
    """The readers point, through `pkit connections resolve --json`. No document at
    all — `pkit` absent, a backbone without the command, a crash — is unresolved,
    with what went wrong."""
    argv = ["pkit", "connections", "resolve", READERS_POINT, "--json"]
    try:
        proc = run(argv, capture_output=True, text=True, check=False)
    except OSError as exc:
        return Readers(False, why=f"`pkit` could not be run to read the point ({exc})")
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        document = None
    if not isinstance(document, Mapping) or "resolved" not in document:
        detail = (proc.stderr or "").strip().splitlines()
        return Readers(
            False,
            why=f"`{' '.join(argv)}` exited {proc.returncode} without its document"
            + (f": {detail[-1]}" if detail else ""),
        )
    return readers_of(document)


def readers_of(document: Mapping[str, Any]) -> Readers:
    """The `pkit connections resolve --json` document as Readers."""
    if document.get("defined") is False:
        return Readers(False, why=f"it is not defined: {document.get('why', '')}")
    if not document.get("resolved"):
        return Readers(False, why=_unresolved_why(document))
    ids = sorted(
        str(entry["id"])
        for entry in document.get("entries") or []
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    )
    return Readers(True, ids=tuple(ids))


def _unresolved_why(document: Mapping[str, Any]) -> str:
    """The backbone's reason, with each inert filler and its own reason."""
    why = str(document.get("why") or "it does not resolve")
    inert = [
        f"{filler.get('name')} ({filler.get('supplies')}): {filler.get('reason')}"
        for filler in document.get("fillers") or []
        if isinstance(filler, Mapping) and filler.get("state") == "inert"
    ]
    return f"{why} — inert: {'; '.join(inert)}" if inert else why


def filler_path(internal_root: str) -> str:
    """Where the project's filler file for the point lives, for a fix to name."""
    return FILLER_SUBPATH if internal_root == "." else f"{internal_root}/{FILLER_SUBPATH}"
