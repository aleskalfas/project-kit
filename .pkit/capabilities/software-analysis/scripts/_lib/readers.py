"""This capability's contribution to the documentation role's readers point (DEC-001 point 8).

`pkit::documentation:readers` is the data point the provider of the
`pkit::documentation` role defines: who reads the documentation and what they
need, one entry per reader — an `id`, the word a page names as its `reader`,
and a `description` of what that reader needs (version 1 of the point's
companion schema, `readers.schema.json`, which its provider ships). The
capability maps its actors onto that shape and keeps its own model to itself:

- **one reader per actor in force**: a withdrawn actor is history, not a
  reader, and an entry whose key is no actor id is the check's to report;
- **its id is the actor's id in lower case**, `ACT-tester` → `act-tester`: a
  word, as the point asks, and an id of this capability's own. It is never one
  of the point's default readers, `user` and `maintainer`, which a
  capability's entry of the same id would replace in the point's `union`, so
  the actors are added beside them;
- **its description** is the actor's name and needs, with the actor's id, so
  a reader-review reads a page against what the analysis says that reader
  needs.

The analysis is read through the backbone's reading, `pkit friction artefacts
--json` (`backbone.read_analysis`): the filler never walks a place, and never
asks for a point.

**Fail closed.** The point's inert policy is `fail`, so what cannot be answered
in full is no answer — raised, never an empty list in its place: the backbone
gives no reading, or the actors' file does not parse or is not a collection. An
analysis with no actors, or no analysis yet, answers the empty list: there is
no reader to add.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from _lib import schemas
from _lib.model import ACTOR, Analysis

#: The point, and the version of its companion schema this contribution targets.
POINT = "pkit::documentation:readers"
POINT_VERSION = 1


class NoAnswer(Exception):
    """The actors cannot be read in full: the filler gives no answer."""


def readers(analysis: Analysis) -> list[dict[str, str]]:
    """The readers the analysis's actors map to, sorted by id. Raises NoAnswer when
    the actors' file cannot be read as a collection of actors."""
    actors_file = analysis.places.get(ACTOR)
    if actors_file is not None and actors_file in analysis.unreadable:
        raise NoAnswer(f"the actors cannot be read: {actors_file}'s front matter does not parse")
    for stray in analysis.strays:
        if stray.kind == ACTOR:
            raise NoAnswer(f"the actors cannot be read: {stray.path} {stray.why}")
    pattern = schemas.id_pattern(ACTOR)
    mapped = [
        reader_of(actor.id, actor.fields)
        for actor in analysis.of_kind(ACTOR)
        if not actor.withdrawn and actor.id is not None and pattern.match(actor.id)
    ]
    return sorted(mapped, key=lambda reader: reader["id"])


def reader_of(actor_id: str, fields: Mapping[str, Any]) -> dict[str, str]:
    """One actor, by its id and its own fields, as a reader of the documentation."""
    return {"id": reader_id(actor_id), "description": _description(actor_id, fields)}


def reader_id(actor_id: str) -> str:
    """The reader an actor is: its id in lower case, `ACT-tester` → `act-tester`."""
    return actor_id.lower()


def envelope(value: Iterable[Mapping[str, str]]) -> dict[str, Any]:
    """The filler envelope the command prints (COR-052 point 6)."""
    return {"schema_version": POINT_VERSION, "value": list(value)}


def _description(actor_id: str, fields: Mapping[str, Any]) -> str:
    """`<name>, the analysis' actor <id>. Needs: <need>; <need>.` The check holds
    the fields to their schema; what is missing here is left out, never refused."""
    name = fields.get("name")
    name = name.strip() if isinstance(name, str) and name.strip() else actor_id
    listed = fields.get("needs")
    needs = [
        need.strip().rstrip(".")
        for need in (listed if isinstance(listed, list) else [])
        if isinstance(need, str) and need.strip().rstrip(".")
    ]
    described = f"{name}, the analysis' actor {actor_id}."
    return f"{described} Needs: {'; '.join(needs)}." if needs else described
