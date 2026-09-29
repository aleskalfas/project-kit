"""The capability's companion schemas: one per artefact kind, and the shapes they share.

Each kind's own fields have a companion schema in `schemas/` (DEC-001 point 2):
`actor`, `term`, `use-case`, `journey`, and `revalidation-record` for the
records. They share `analysis.schema.json` — each kind's id, the status, a line
of text — which is also where the commands read the id patterns from, so the
stamp that gives an id and the check that judges one never disagree. The
friction block beside the own fields is the core's shape, validated by the
backbone, and never here.
"""

from __future__ import annotations

import functools
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from _lib.model import ACTOR, JOURNEY, TERM, USE_CASE

#: Where the schemas are, in the capability's own tree.
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"

#: The shared definitions, and the kind of front matter a revalidation record is.
SHARED = "analysis"
RECORD = "revalidation-record"

#: Each kind's schema, by file stem.
SCHEMA_OF = {ACTOR: "actor", TERM: "term", USE_CASE: "use-case", JOURNEY: "journey", RECORD: RECORD}

#: Each kind's id, as a definition of the shared schema.
ID_DEF = {ACTOR: "actor-id", TERM: "term-id", USE_CASE: "use-case-id", JOURNEY: "journey-id"}


@functools.cache
def _schemas() -> dict[str, dict[str, Any]]:
    return {
        stem: json.loads((SCHEMAS / f"{stem}.schema.json").read_text(encoding="utf-8"))
        for stem in (SHARED, *SCHEMA_OF.values())
    }


@functools.cache
def _registry() -> Registry:
    return Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in _schemas().values()
    )


@functools.cache
def validator(kind: str) -> Draft202012Validator:
    """The validator of one kind's own fields — or a revalidation record's front matter."""
    return Draft202012Validator(_schemas()[SCHEMA_OF[kind]], registry=_registry())


def definition(name: str) -> Mapping[str, Any]:
    """One definition of the shared schema."""
    return _schemas()[SHARED]["$defs"][name]


@functools.cache
def id_pattern(kind: str) -> re.Pattern[str]:
    """The pattern a kind's id has."""
    return re.compile(definition(ID_DEF[kind])["pattern"])


@functools.cache
def slug_pattern() -> re.Pattern[str]:
    return re.compile(definition("slug")["pattern"])


def errors(kind: str, fields: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Each way `fields` falls short of the kind's schema: a JSON Pointer into
    them and the message, in a stable order."""
    return sorted(
        (_pointer(error.absolute_path), error.message)
        for error in validator(kind).iter_errors(dict(fields))
    )


def _pointer(path: Any) -> str:
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in path)
