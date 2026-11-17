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

The document is read by its keys (ADR-097 point 3). The point holds every reader
only where it resolved with each filler `taken` or `passed over`: a filler in a
state this capability does not know may not have answered, so the readers it
would have given cannot be told. That, a key the reading needs that is missing,
null or of another type, and a version it does not know each leave the point
unresolved, with why, never read as the readers it lists.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from _lib import backbone
from _lib import document_keys as keys

#: The point, and where a project's own filler file for it lives, under the
#: internal documentation root (the lifecycle README, "Where a project filler
#: file lives").
READERS_POINT = "pkit::documentation:readers"
FILLER_SUBPATH = "pkit/fillers/pkit/documentation/readers.yaml"

#: The version of the point's document this reading understands. A document without
#: `schema_version` comes from a backbone that predates the key: version 1 (the CLI
#: reference, `connections resolve`).
DOCUMENT_VERSION = 1

#: The states of a filler that answered, or was not meant to (COR-052 point 6).
ANSWERED = frozenset({"taken", "passed over"})
INERT = "inert"

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Readers:
    """The readers point as it resolved: the reader ids, or why there are none."""

    resolved: bool
    ids: tuple[str, ...] = ()  # sorted
    why: str = ""  # when unresolved


def read_readers(run: Runner = backbone.run) -> Readers:
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
    command = f"`pkit connections resolve {READERS_POINT} --json`"
    version = document.get("schema_version", DOCUMENT_VERSION)
    if type(version) is not int or version != DOCUMENT_VERSION:
        return Readers(
            False,
            why=f"{command} answered schema_version {version!r}; this capability reads "
            f"{DOCUMENT_VERSION}",
        )
    try:
        return _readers(document)
    except keys.Untold as exc:
        return Readers(
            False, why=f"{command} answered a document this capability cannot read: {exc}"
        )


def _readers(document: Mapping[str, Any]) -> Readers:
    if not keys.flag(document, "defined", ""):
        return Readers(False, why=f"it is not defined: {keys.text(document, 'why', '')}")
    if not keys.flag(document, "resolved", ""):
        return Readers(False, why=_unresolved_why(document))
    untold = [
        f"{keys.text(filler, 'name', where)} ({keys.text(filler, 'state', where)})"
        for where, filler in keys.objects(document, "fillers", "")
        if keys.text(filler, "state", where) not in ANSWERED
    ]
    if untold:
        return Readers(
            False,
            why=f"a filler's readers cannot be told, since its state is not one in which it "
            f"answered: {'; '.join(untold)}",
        )
    ids = sorted(
        keys.text(entry, "id", where) for where, entry in keys.objects(document, "entries", "")
    )
    return Readers(True, ids=tuple(ids))


def _unresolved_why(document: Mapping[str, Any]) -> str:
    """The backbone's reason, with each inert filler and its own reason."""
    why = keys.text(document, "why", "") or "it does not resolve"
    inert = [
        f"{keys.text(filler, 'name', where)} ({keys.text(filler, 'supplies', where)}): "
        f"{keys.text(filler, 'reason', where)}"
        for where, filler in keys.objects(document, "fillers", "")
        if keys.text(filler, "state", where) == INERT
    ]
    return f"{why} — inert: {'; '.join(inert)}" if inert else why


def filler_path(internal_root: str) -> str:
    """Where the project's filler file for the point lives, for a fix to name."""
    return FILLER_SUBPATH if internal_root == "." else f"{internal_root}/{FILLER_SUBPATH}"
