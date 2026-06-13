"""Tests for the `project_kit.schemas` consumer API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_kit.schemas import (
    SchemaLookupError,
    clear_cache,
    find_namespace_owner,
    iter_entries,
    load_schema,
    resolve_token,
)


# Fixtures --------------------------------------------------------------


def _setup_demo_capability(target_root: Path) -> Path:
    """Stamp a capability + a namespace-owning schema."""
    schemas = target_root / ".pkit" / "capabilities" / "demo" / "schemas"
    schemas.mkdir(parents=True)
    yaml_body = (
        "schema_version: 1\n"
        "types:\n"
        "  task:\n"
        "    role: A unit of work.\n"
        "  feature:\n"
        "    role: A coherent capability.\n"
    )
    (schemas / "issue-types.yaml").write_text(yaml_body, encoding="utf-8")
    companion = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "issue-types.schema.json",
        "x-pkit-id-collection": "/types",
        "type": "object",
        "required": ["schema_version", "types"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "types": {
                "type": "object",
                "patternProperties": {"^[a-z][a-z0-9-]*$": {"type": "object"}},
                "additionalProperties": False,
            },
        },
    }
    (schemas / "issue-types.schema.json").write_text(json.dumps(companion), encoding="utf-8")
    return schemas


@pytest.fixture(autouse=True)
def _isolated_cache() -> None:
    """Ensure each test starts with a clean cache (load_schema is LRU-cached)."""
    clear_cache()
    yield
    clear_cache()


# load_schema -----------------------------------------------------------


def test_load_schema_returns_parsed_yaml(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    data = load_schema(tmp_path, "demo", "issue-types")
    assert data["schema_version"] == 1
    assert "task" in data["types"]


def test_load_schema_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(SchemaLookupError, match="YAML file"):
        load_schema(tmp_path, "demo", "missing")


def test_load_schema_caches(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    a = load_schema(tmp_path, "demo", "issue-types")
    b = load_schema(tmp_path, "demo", "issue-types")
    # Same object identity — LRU cache returned the cached entry.
    assert a is b


def test_clear_cache_drops_cached_data(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    a = load_schema(tmp_path, "demo", "issue-types")
    clear_cache()
    b = load_schema(tmp_path, "demo", "issue-types")
    assert a is not b


# iter_entries ----------------------------------------------------------


def test_iter_entries_walks_mapping_collection(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    entries = list(iter_entries(tmp_path, "demo", "issue-types"))
    ids = [eid for eid, _ in entries]
    assert ids == ["task", "feature"]
    for eid, data in entries:
        assert "role" in data


def test_iter_entries_walks_list_collection(tmp_path: Path) -> None:
    schemas = tmp_path / ".pkit" / "capabilities" / "demo" / "schemas"
    schemas.mkdir(parents=True)
    yaml_body = (
        "schema_version: 1\n"
        "items:\n"
        "  - id: alpha\n"
        "    label: Alpha\n"
        "  - id: beta\n"
        "    label: Beta\n"
    )
    (schemas / "list-ns.yaml").write_text(yaml_body, encoding="utf-8")
    companion = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "x-pkit-id-collection": "/items",
        "type": "object",
        "required": ["schema_version", "items"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {"id": {"type": "string"}},
                },
            },
        },
    }
    (schemas / "list-ns.schema.json").write_text(json.dumps(companion), encoding="utf-8")
    entries = list(iter_entries(tmp_path, "demo", "list-ns"))
    assert [eid for eid, _ in entries] == ["alpha", "beta"]


def test_iter_entries_raises_when_schema_has_no_namespace(tmp_path: Path) -> None:
    schemas = tmp_path / ".pkit" / "capabilities" / "demo" / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "consumer.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    companion = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        # No `x-pkit-id-collection`.
        "type": "object",
        "properties": {"schema_version": {"type": "integer", "const": 1}},
    }
    (schemas / "consumer.schema.json").write_text(json.dumps(companion), encoding="utf-8")
    with pytest.raises(SchemaLookupError, match="doesn't own an id collection"):
        list(iter_entries(tmp_path, "demo", "consumer"))


def test_iter_entries_raises_when_companion_missing(tmp_path: Path) -> None:
    schemas = tmp_path / ".pkit" / "capabilities" / "demo" / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "orphan.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    with pytest.raises(SchemaLookupError, match="companion"):
        list(iter_entries(tmp_path, "demo", "orphan"))


# resolve_token ---------------------------------------------------------


def test_resolve_token_returns_entry_data(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    data = resolve_token(tmp_path, "[issue-types:task]")
    assert data["role"] == "A unit of work."


def test_resolve_token_raises_on_malformed(tmp_path: Path) -> None:
    with pytest.raises(SchemaLookupError, match="not a typed token"):
        resolve_token(tmp_path, "issue-types:task")  # no brackets


def test_resolve_token_raises_on_unknown_namespace(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    with pytest.raises(SchemaLookupError, match="namespace 'nope'"):
        resolve_token(tmp_path, "[nope:task]")


def test_resolve_token_raises_on_unknown_id(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    with pytest.raises(SchemaLookupError, match="id 'bogus'"):
        resolve_token(tmp_path, "[issue-types:bogus]")


# find_namespace_owner --------------------------------------------------


def test_find_namespace_owner_returns_capability(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    assert find_namespace_owner(tmp_path, "issue-types") == "demo"


def test_find_namespace_owner_returns_none_for_unknown(tmp_path: Path) -> None:
    _setup_demo_capability(tmp_path)
    assert find_namespace_owner(tmp_path, "nope") is None
