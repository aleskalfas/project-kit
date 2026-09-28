"""Staging synthetic capabilities that declare connections (COR-053), shared by
the tests of the wiring graph, the provider selection and the status report.

A staged capability is registered as incubated, so its package file is its
version of record, and carries a `publish` query command for any filler,
event or subscription to name.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from project_kit.report_context import project_config_path
from tests.adopter_repo import AdopterRepo

DOCS = "pkit::documentation"
READERS = f"{DOCS}:readers"
PAGE_CREATED = f"{DOCS}:page-created"
REVIEW = f"{DOCS}:review"
GLOSSARY = "pkit::analysis:glossary"
READERS_FILLER = "docs/pkit/fillers/pkit/documentation/readers.yaml"

READERS_SCHEMA = {"type": "array", "items": {"type": "string"}}
PAYLOAD_SCHEMA = {"type": "object", "properties": {"page": {"type": "string"}}}
SCHEMAS = {"readers.schema.json": READERS_SCHEMA, "page-created.schema.json": PAYLOAD_SCHEMA}


def stage(
    repo: AdopterRepo,
    name: str,
    connections: dict[str, Any] | None = None,
    *,
    definitions: dict[str, str] | None = None,
) -> Path:
    """Write `.pkit/capabilities/<name>/` — package, companion schemas, process
    definitions (`<process-id>.yaml` → its text) — and register it as incubated."""
    cap_dir = repo.pkit / "capabilities" / name
    (cap_dir / "scripts").mkdir(parents=True, exist_ok=True)
    (cap_dir / "scripts" / "publish.py").write_text("", encoding="utf-8")
    (cap_dir / "schemas").mkdir(exist_ok=True)
    for file, schema in SCHEMAS.items():
        (cap_dir / "schemas" / file).write_text(json.dumps(schema), encoding="utf-8")
    for process_id, text in (definitions or {}).items():
        (cap_dir / "schemas" / f"{process_id}.yaml").write_text(text, encoding="utf-8")
    package: dict[str, Any] = {
        "schema_version": 2,
        "component": {"kind": "capability", "name": name, "version": "0.1.0"},
        "description": f"Synthetic {name}.",
        "requires_backbone": ">=0.0.0",
        "commands": {
            "publish": {"script": "scripts/publish.py", "help": "Publish.", "query-contract": True}
        },
    }
    if connections is not None:
        package["connections"] = connections
    with (cap_dir / "package.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(package, handle)
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    if not any(e.name == name for e in backbone.components):
        backbone.components.append(
            ComponentRegistryEntry(
                kind="capability",
                name=name,
                manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
                origin="incubated-in-repo",
            )
        )
        write_backbone_manifest(repo.root, backbone)
    return cap_dir / "package.yaml"


def provider(
    *,
    role: str = DOCS,
    accepts: dict[str, Any] | None = None,
    offers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A `connections` block providing `role` with these points."""
    points: dict[str, Any] = {}
    if accepts is not None:
        points["accepts"] = accepts
    if offers is not None:
        points["offers"] = offers
    return {"roles": [role], "extension-points": points}


def data_point(version: int = 1, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": version,
        "schema": "readers.schema.json",
        "description": "Who reads the documentation.",
        **extra,
    }


def event_point(version: int = 1) -> dict[str, Any]:
    return {
        "kind": "event",
        "schema_version": version,
        "description": "A page was written.",
        "command": "publish",
        "schema": "page-created.schema.json",
        "subject": "page",
    }


def process_point(process_id: str, version: int = 1) -> dict[str, Any]:
    return {
        "kind": "process",
        "schema_version": version,
        "description": "The review process others may wait on.",
        "process": process_id,
    }


def contributes(point: str = READERS, version: int = 1, **extra: Any) -> dict[str, Any]:
    """A `connections` block contributing a value to `point`."""
    entry = {"point": point, "schema_version": version, "value": ["operator"], **extra}
    return {"extensions": {"contributes": [entry]}}


def write_config(repo: AdopterRepo, text: str) -> None:
    path = project_config_path(repo.root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def definition(process_id: str, states: str) -> str:
    """A minimal process definition; `states` is the YAML of its state list,
    indented four spaces."""
    return (
        f"process:\n  id: {process_id}\n  version: 1\n  subject:\n    cardinality: singleton\n"
        f"  states:\n{states}  transitions: []\n"
    )


def state(state_id: str, extra: str = "") -> str:
    """One state of `definition`; `extra` is further YAML, indented six spaces."""
    return (
        f"    - id: {state_id}\n      meaning: {state_id}.\n      entry: true\n"
        f"      detection:\n        mode: inferred\n        predicate:\n          run: publish\n"
        f"{extra}"
    )
