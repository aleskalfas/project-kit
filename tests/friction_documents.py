"""Documents and configuration for the friction tests (COR-050).

Shared by the change-check and whole-repository-check tests: a backbone
configuration with a `friction` key, and Markdown documents whose front
matter carries the `friction` block. Front matter is written as JSON — valid
YAML, and exact about strings — so a test says precisely what an artefact
holds.
"""

from __future__ import annotations

import json
from typing import Any

CONFIG = ".pkit/project/config.yaml"
T1 = "2026-10-01T09:00:00Z"
T2 = "2026-10-02T09:40:12Z"
SOURCE = {"src/cli/main.py": "print('cli')\n", "src/core/engine.py": "ENGINE = 1\n"}


def friction_config(
    mode: str = "warning", places: tuple[str, ...] = ("docs",), **friction: Any
) -> str:
    """The backbone configuration file with a `friction` key: mode, places, and the rest."""
    block: dict[str, Any] = {"mode": mode, "places": list(places), **friction}
    return json.dumps({"name": "adopter", "friction": block}, indent=2) + "\n"


def document(
    artefact_id: str | None,
    *,
    anchors: dict[str, list[str]] | None = None,
    at: str | None = None,
    outcome: str | None = None,
    because: str | None = None,
    deferred: list[tuple[str, str, str]] | None = None,
    body: str = "Body.",
    **fields: Any,
) -> str:
    """A document whose front matter carries the `friction` block, as JSON."""
    front: dict[str, Any] = {} if artefact_id is None else {"id": artefact_id}
    front.update(fields)
    revalidated: dict[str, Any] = {}
    if at is not None:
        revalidated["at"] = at
    if outcome is not None:
        revalidated["outcome"] = outcome
    if because is not None:
        revalidated["unchanged-because"] = because
    if deferred:
        revalidated["deferred"] = [
            {"anchor": {"kind": kind, "value": value}, "reason": reason}
            for kind, value, reason in deferred
        ]
    block: dict[str, Any] = {}
    if anchors is not None:
        block["anchors"] = anchors
    if revalidated:
        block["revalidated"] = revalidated
    front["pkit"] = {"friction": block}
    return f"---\n{json.dumps(front, indent=2)}\n---\n\n{body}\n"


def guide(**overrides: Any) -> str:
    """The workhorse artefact: `guide`, anchored to the CLI sources, revalidated at T1."""
    values: dict[str, Any] = {
        "anchors": {"path": ["src/cli/**"]},
        "at": T1,
        "outcome": "unchanged",
        "because": "the CLI surface is as described",
    }
    values.update(overrides)
    return document("guide", **values)
