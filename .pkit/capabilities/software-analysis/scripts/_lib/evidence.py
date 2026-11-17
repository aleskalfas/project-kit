"""The evidence point, read as it resolves (DEC-001 point 7).

`pkit::analysis:revalidation-evidence` is the data point this capability
defines as the provider of the `pkit::analysis` role (COR-052, COR-053):
executed results that confirm or refute an artefact at a commit, one entry per
result, keyed by three parts, `<artefact>@<commit>#<check>`. The check is the
name its filler gives one executed check, kept from commit to commit, and opens
with the filler's own name — a capability's, or `project` for a project file's —
so two fillers' results for one artefact at one commit stand side by side, and
only two that claim one check collide. Its value is `union`, no default takes
part, and its inert policy is `fallback`: the evidence advises, so a filler that
cannot answer is warned and the rest still count.

The backbone resolves the point and applies its companion schema,
`schemas/revalidation-evidence.schema.json`, to every filler — a project
filler that does not fit is the project's error, a capability's is inert — so
what resolves fits the schema, and this reading applies nothing again (ADR-057
point 2). It is read through `pkit connections resolve --json`
(`backbone.read_point`), and only when a revalidation record copies evidence.
Each entry is kept with its origin — the capability that supplied it, or the
project's filler — since the opening name is a convention the check warns on
for a capability's entry, and never for the project's: the project replaces a
capability's entry by writing one under that capability's check.

Evidence informs a revalidation and never replaces it. A record copies each
entry it draws on whole, since the record is history and the point holds only
what its fillers report now; the check compares a copy with the entry the
point now holds under its id (`_lib/check.py`).
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _lib import backbone
from _lib import document_keys as keys
from _lib.model import Unreadable

#: The point, by its address.
POINT = "pkit::analysis:revalidation-evidence"

#: The origins the resolved document gives an entry no capability supplied: the
#: project's filler file, and the definer's default, which takes no part here
#: (the CLI README, "Connections commands").
PROJECT, DEFAULT = "project filler", "the default"


@dataclass(frozen=True)
class Held:
    """One entry the point holds: its value, and where it came from — a capability,
    by name, or `PROJECT`."""

    value: Mapping[str, Any]
    origin: str

    @property
    def from_capability(self) -> bool:
        return self.origin not in (PROJECT, DEFAULT)


@dataclass(frozen=True)
class Evidence:
    """The evidence point as it resolved: each entry it holds, by id, or why it
    holds none."""

    resolved: bool
    entries: Mapping[str, Held] = field(default_factory=dict[str, Held])
    why: str = ""


def own_id(entry: Mapping[str, Any]) -> str:
    """The id an entry's own fields make, `<artefact>@<commit>#<check>`: what its
    `id` is, though a schema cannot compare fields to say so."""
    return f"{entry['artefact']}@{entry['commit']}#{entry['check']}"


def opening(check: str) -> str:
    """A check's opening name, its first dotted word: the filler's own name."""
    return check.split(".", 1)[0]


def read_evidence(root: Path, run: backbone.Runner = subprocess.run) -> Evidence:
    """The evidence point, through `pkit connections resolve --json`. No document at
    all — `pkit` absent, a backbone without the command, a crash — is unresolved,
    with what went wrong."""
    try:
        document = backbone.read_point(root, POINT, run)
    except Unreadable as exc:
        return Evidence(False, why=str(exc))
    return evidence_of(document)


#: The version of the point's document this reading understands. A document without
#: `schema_version` comes from a backbone that predates the key: version 1 (the CLI
#: reference, `connections resolve`).
DOCUMENT_VERSION = 1

#: The states the backbone gives a filler (COR-052 point 6; the CLI reference,
#: `connections resolve`): one that answered, one that was meant to and could not, and
#: one not asked.
FILLER_STATES = frozenset({"taken", "inert", "passed over"})


def evidence_of(document: Mapping[str, Any]) -> Evidence:
    """The `pkit connections resolve --json` document as Evidence. It is read by its keys
    (ADR-097 point 3): the point holds its entries where it resolved with each filler in
    a state this reading knows. An `inert` filler supplied nothing, and the point's
    `fallback` policy keeps the rest, so its entries are read; a filler in a state this
    reading does not know may have answered, so the point is unresolved. That, a key the
    reading needs that is missing, null or of another type, and a version it does not
    know each leave the point unresolved, with why. An entry whose value is not an object
    is no evidence, as before."""
    command = f"`pkit connections resolve {POINT} --json`"
    version = document.get("schema_version", DOCUMENT_VERSION)
    if type(version) is not int or version != DOCUMENT_VERSION:
        return Evidence(
            False,
            why=f"{command} answered schema_version {version!r}; this capability reads "
            f"{DOCUMENT_VERSION}",
        )
    try:
        return _evidence(document)
    except keys.Untold as exc:
        return Evidence(
            False, why=f"{command} answered a document this capability cannot read: {exc}"
        )


def _evidence(document: Mapping[str, Any]) -> Evidence:
    if not keys.flag(document, "defined", ""):
        return Evidence(False, why=f"it is not defined: {keys.text(document, 'why', '')}")
    if not keys.flag(document, "resolved", ""):
        return Evidence(False, why=keys.text(document, "why", "") or "it does not resolve")
    untold = [
        f"{keys.text(filler, 'name', where)} ({keys.text(filler, 'state', where)})"
        for where, filler in keys.objects(document, "fillers", "")
        if keys.text(filler, "state", where) not in FILLER_STATES
    ]
    if untold:
        return Evidence(
            False,
            why=f"a filler's evidence cannot be told, since its state is not one this "
            f"capability knows: {'; '.join(untold)}",
        )
    entries: dict[str, Held] = {}
    for where, entry in keys.objects(document, "entries", ""):
        value, origin = keys.value(entry, "value", where), keys.text(entry, "origin", where)
        if isinstance(value, Mapping):
            entries[keys.text(entry, "id", where)] = Held(value, origin)
    return Evidence(True, entries=entries)
