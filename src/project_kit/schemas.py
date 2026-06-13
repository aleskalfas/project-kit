"""Public API for code that **consumes** schemas at runtime.

`pkit schemas validate` validates schemas; `project_kit.schemas` is the
read-side companion — the API skills, agents, and scripts use to load
a schema's data and resolve typed-token references at runtime.

The functions here are thin, focused, and cache-aware. Each call either
returns parsed data ready for the consumer to act on, or raises a
`SchemaLookupError` with an actionable message naming what went wrong.

Typical usage:

    from pathlib import Path
    from project_kit.schemas import load_schema, resolve_token, iter_entries

    root = Path(...)  # project root containing .pkit/

    # Load a full schema's parsed YAML.
    workflow = load_schema(root, "project-management", "workflow")
    for state_id, state in workflow["states"].items():
        ...

    # Walk a namespace's entries with id + data pairs.
    for type_id, type_def in iter_entries(root, "project-management", "issue-types"):
        print(type_id, type_def.get("role", ""))

    # Resolve a typed token to its target entry.
    severity = resolve_token(root, "[validation-severity:hard-reject]")
    print(severity["description"])

Caching: every call caches the parsed YAML keyed by `(target_root, capability,
name)`, so repeated reads in the same process hit memory. Call
`clear_cache()` to force a re-read (e.g., after editing schemas on disk
during a long-running agent session).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from project_kit.schemas_validate import (
    _ID_COLLECTION_ANNOTATION,
    _TOKEN_PATTERN,
    _resolve_json_pointer,
    _stringify_dates,
    _yaml,
)


class SchemaLookupError(LookupError):
    """Raised when a schema, namespace, or token cannot be resolved at runtime.

    The exception's message names what was being looked up and why it
    failed (missing file, missing collection annotation, malformed token,
    unknown id, etc.) — sufficient for the consumer's own error handling
    or surfacing to a user.
    """


def load_schema(target_root: Path, capability: str, name: str) -> Any:
    """Load and return the parsed YAML for one schema.

    `target_root` is the project root containing `.pkit/`. `capability` is
    the capability's name (`project-management`, etc.); `name` is the
    schema's YAML stem (`issue-types`, `workflow`, etc.).

    Result is the YAML data, with `datetime.date` values coerced to ISO
    strings (matching what the validator sees). Cached per
    `(target_root, capability, name)`; call `clear_cache()` to invalidate.

    Raises `SchemaLookupError` if the schema doesn't exist or fails to
    parse.
    """
    cache_key = (str(target_root.resolve()), capability, name)
    return _load_cached(cache_key)


def iter_entries(
    target_root: Path, capability: str, name: str
) -> Iterator[tuple[str, Any]]:
    """Iterate `(id, entry_data)` pairs for a namespace's id collection.

    Requires the schema's companion to declare `x-pkit-id-collection`
    (i.e., the schema must own a namespace). Resolves the pointer in the
    YAML data and yields each entry's id alongside its data. Supports
    both mapping-form collections (ids are keys) and list-of-objects
    collections (ids are each item's `id` field).

    Raises `SchemaLookupError` if the schema doesn't own a namespace
    (no annotation), if the companion is missing/malformed, or if the
    pointer doesn't resolve.
    """
    capability_dir = target_root / ".pkit" / "capabilities" / capability / "schemas"
    companion_path = capability_dir / f"{name}.schema.json"
    if not companion_path.is_file():
        raise SchemaLookupError(
            f"capability {capability!r} schema {name!r}: companion "
            f"{companion_path} not found."
        )
    try:
        schema = json.loads(companion_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SchemaLookupError(
            f"capability {capability!r} schema {name!r}: companion "
            f"{companion_path} is not valid JSON: {exc.msg}."
        ) from exc
    pointer = schema.get(_ID_COLLECTION_ANNOTATION)
    if not isinstance(pointer, str):
        raise SchemaLookupError(
            f"capability {capability!r} schema {name!r}: companion lacks "
            f"the {_ID_COLLECTION_ANNOTATION!r} annotation, so it doesn't "
            f"own an id collection. Use load_schema() instead to read the "
            f"YAML directly."
        )
    data = load_schema(target_root, capability, name)
    try:
        collection = _resolve_json_pointer(data, pointer)
    except (KeyError, ValueError) as exc:
        raise SchemaLookupError(
            f"capability {capability!r} schema {name!r}: "
            f"{_ID_COLLECTION_ANNOTATION} pointer {pointer!r} did not resolve: {exc}."
        ) from exc
    if isinstance(collection, dict):
        for key, value in collection.items():
            yield str(key), value
    elif isinstance(collection, list):
        for item in collection:
            if isinstance(item, dict) and "id" in item:
                yield str(item["id"]), item
    else:
        raise SchemaLookupError(
            f"capability {capability!r} schema {name!r}: "
            f"{_ID_COLLECTION_ANNOTATION} pointer {pointer!r} resolved to "
            f"{type(collection).__name__}; expected mapping or list-of-objects-with-id."
        )


def resolve_token(target_root: Path, token: str) -> Any:
    """Resolve a typed token (`[<namespace>:<id>]`) to its target entry data.

    Walks every installed capability's schemas to find the one whose YAML
    stem matches `<namespace>` and whose companion has the
    `x-pkit-id-collection` annotation. Returns the entry's data (the
    mapping value or list item) for the matching id.

    Raises `SchemaLookupError` for malformed tokens, missing namespaces,
    or unknown ids.
    """
    m = _TOKEN_PATTERN.match(token)
    if m is None:
        raise SchemaLookupError(
            f"not a typed token: {token!r}. Expected shape `[<namespace>:<id>]` "
            f"with both halves kebab-case."
        )
    namespace, id_value = m.group(1), m.group(2)
    capability = _find_capability_for_namespace(target_root, namespace)
    if capability is None:
        raise SchemaLookupError(
            f"namespace {namespace!r} not found among installed capabilities."
        )
    for entry_id, entry_data in iter_entries(target_root, capability, namespace):
        if entry_id == id_value:
            return entry_data
    raise SchemaLookupError(
        f"id {id_value!r} not found in namespace {namespace!r} "
        f"(owned by capability {capability!r})."
    )


def find_namespace_owner(target_root: Path, namespace: str) -> str | None:
    """Locate which capability owns the named namespace.

    Returns the capability's name, or None if no installed capability
    declares the namespace. Useful when a caller wants to introspect
    layout before reading.
    """
    return _find_capability_for_namespace(target_root, namespace)


def clear_cache() -> None:
    """Drop the cached parsed-YAML store. Call after on-disk edits during a long session."""
    _load_cached.cache_clear()


# --- internals ---------------------------------------------------------


@lru_cache(maxsize=256)
def _load_cached(cache_key: tuple[str, str, str]) -> Any:
    """LRU-cached schema loader keyed by (resolved_target_root, capability, name)."""
    target_root_str, capability, name = cache_key
    target_root = Path(target_root_str)
    yaml_path = (
        target_root / ".pkit" / "capabilities" / capability / "schemas" / f"{name}.yaml"
    )
    if not yaml_path.is_file():
        raise SchemaLookupError(
            f"capability {capability!r} schema {name!r}: YAML file "
            f"{yaml_path} not found."
        )
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SchemaLookupError(
            f"capability {capability!r} schema {name!r}: could not read "
            f"{yaml_path}: {exc}."
        ) from exc
    try:
        data = _yaml.load(text)
    except Exception as exc:  # ruamel.yaml raises various YAMLError subclasses
        raise SchemaLookupError(
            f"capability {capability!r} schema {name!r}: YAML parse error: {exc}."
        ) from exc
    return _stringify_dates(data)


def _find_capability_for_namespace(target_root: Path, namespace: str) -> str | None:
    """Walk capabilities looking for the one that owns `namespace`.

    A capability owns the namespace if its schemas dir contains
    `<namespace>.yaml` AND the matching `<namespace>.schema.json` declares
    `x-pkit-id-collection`. Returns the first match (deterministic by
    sorted order); None if no match.
    """
    capabilities_dir = target_root / ".pkit" / "capabilities"
    if not capabilities_dir.is_dir():
        return None
    for cap_dir in sorted(capabilities_dir.iterdir()):
        if not cap_dir.is_dir():
            continue
        companion = cap_dir / "schemas" / f"{namespace}.schema.json"
        if not companion.is_file():
            continue
        try:
            schema = json.loads(companion.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(schema.get(_ID_COLLECTION_ANNOTATION), str):
            return cap_dir.name
    return None
