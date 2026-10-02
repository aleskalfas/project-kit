"""The evidence point, read as it resolves (DEC-001 point 7).

`pkit::analysis:revalidation-evidence` is the data point this capability
defines as the provider of the `pkit::analysis` role (COR-052, COR-053):
executed results that confirm or refute an artefact at a commit, one entry per
artefact and commit, keyed `<artefact>@<commit>`. Its value is `union`, no
default takes part, and its inert policy is `fallback`: the evidence advises,
so a filler that cannot answer is warned and the rest still count.

The backbone resolves the point and applies its companion schema,
`schemas/revalidation-evidence.schema.json`, to every filler — a project
filler that does not fit is the project's error, a capability's is inert — so
what resolves fits the schema, and this reading applies nothing again (ADR-057
point 2). It is read through `pkit connections resolve --json`
(`backbone.read_point`), and only when a revalidation record copies evidence.

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
from _lib.model import Unreadable

#: The point, by its address.
POINT = "pkit::analysis:revalidation-evidence"


@dataclass(frozen=True)
class Evidence:
    """The evidence point as it resolved: each entry it holds, by id, or why it
    holds none."""

    resolved: bool
    entries: Mapping[str, Mapping[str, Any]] = field(default_factory=dict[str, Mapping[str, Any]])
    why: str = ""


def read_evidence(root: Path, run: backbone.Runner = subprocess.run) -> Evidence:
    """The evidence point, through `pkit connections resolve --json`. No document at
    all — `pkit` absent, a backbone without the command, a crash — is unresolved,
    with what went wrong."""
    try:
        document = backbone.read_point(root, POINT, run)
    except Unreadable as exc:
        return Evidence(False, why=str(exc))
    return evidence_of(document)


def evidence_of(document: Mapping[str, Any]) -> Evidence:
    """The `pkit connections resolve --json` document as Evidence."""
    if document.get("defined") is False:
        return Evidence(False, why=f"it is not defined: {document.get('why', '')}")
    if not document.get("resolved"):
        return Evidence(False, why=str(document.get("why") or "it does not resolve"))
    entries = {
        str(entry["id"]): entry["value"]
        for entry in document.get("entries") or []
        if isinstance(entry, Mapping)
        and isinstance(entry.get("id"), str)
        and isinstance(entry.get("value"), Mapping)
    }
    return Evidence(True, entries=entries)
