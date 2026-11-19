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

    # The reserved owner `core` names the core schemas area (`.pkit/schemas/`).
    catalog = load_schema(root, "core", "privilege-catalog")

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
    _TOKEN_PATTERN,
    NAMESPACE_OWNER_ANNOTATIONS,
    _stringify_dates,
    _yaml,
    iter_schema_homes,
    namespace_entries,
    namespace_ownership,
    owner_label,
    schemas_home,
    unknown_namespace_message,
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
    the owner's name — a capability (`project-management`, etc.) or the
    reserved `core` for the core schemas area (`.pkit/schemas/`); `name` is
    the schema's YAML stem (`issue-types`, `workflow`, etc.).

    Result is the YAML data, with `datetime.date` values coerced to ISO
    strings (matching what the validator sees). Cached per
    `(target_root, capability, name)`; call `clear_cache()` to invalidate.

    Raises `SchemaLookupError` if the schema doesn't exist or fails to
    parse.
    """
    cache_key = (str(target_root.resolve()), capability, name)
    return _load_cached(cache_key)


def iter_entries(target_root: Path, capability: str, name: str) -> Iterator[tuple[str, Any]]:
    """Iterate `(id, entry_data)` pairs for a namespace's entries.

    Requires the schema to own a namespace: its companion declares
    `x-pkit-id-collection`, or `x-pkit-entry-id` for a document schema.
    A collection yields each entry's id alongside its data, for both
    mapping-form collections (ids are keys) and list-of-objects
    collections (ids are each item's `id` field). A document schema's YAML
    is its one document, so it yields that document's own id with the
    whole document (COR-029 point 6).

    Raises `SchemaLookupError` if the schema doesn't own a namespace
    (no annotation), if the companion is missing/malformed or declares
    both annotations, or if the pointer doesn't reach the ids.
    """
    companion_path = schemas_home(target_root, capability) / f"{name}.schema.json"
    if not companion_path.is_file():
        raise SchemaLookupError(
            f"{owner_label(capability)} schema {name!r}: companion {companion_path} not found."
        )
    try:
        schema = json.loads(companion_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SchemaLookupError(
            f"{owner_label(capability)} schema {name!r}: companion "
            f"{companion_path} is not valid JSON: {exc.msg}."
        ) from exc
    ownership = namespace_ownership(schema)
    if ownership is None:
        raise SchemaLookupError(
            f"{owner_label(capability)} schema {name!r}: companion declares no "
            f"{NAMESPACE_OWNER_ANNOTATIONS}, so it doesn't own a namespace. Use "
            f"load_schema() instead to read the YAML directly."
        )
    if isinstance(ownership, str):
        raise SchemaLookupError(
            f"{owner_label(capability)} schema {name!r}: companion {ownership}."
        )
    entries = namespace_entries(ownership, load_schema(target_root, capability, name))
    if isinstance(entries, str):
        raise SchemaLookupError(f"{owner_label(capability)} schema {name!r}: {entries}.")
    yield from entries


def resolve_token(target_root: Path, token: str) -> Any:
    """Resolve a typed token (`[<namespace>:<id>]`) to its target entry data.

    Walks every schemas home (the core schemas area, then every installed
    capability) to find the schema whose YAML stem matches `<namespace>`
    and whose companion declares the annotation that makes it the
    namespace's owner. Returns the entry's data (the mapping value or list
    item, or a document schema's whole document) for the matching id.

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
    capability = _find_owner_for_namespace(target_root, namespace)
    if capability is None:
        raise SchemaLookupError(unknown_namespace_message(namespace))
    for entry_id, entry_data in iter_entries(target_root, capability, namespace):
        if entry_id == id_value:
            return entry_data
    raise SchemaLookupError(
        f"id {id_value!r} not found in namespace {namespace!r} "
        f"(owned by {owner_label(capability)})."
    )


def find_namespace_owner(target_root: Path, namespace: str) -> str | None:
    """Locate which owner declares the named namespace.

    Returns the owner's name — a capability's name, or `core` when the
    namespace lives in the core schemas area (`.pkit/schemas/`) — or None
    if no schemas home declares it. Pass the result to `load_schema` /
    `iter_entries`, or map it to a directory via
    `schemas_validate.schemas_home`.
    """
    return _find_owner_for_namespace(target_root, namespace)


def clear_cache() -> None:
    """Drop the cached parsed-YAML store. Call after on-disk edits during a long session."""
    _load_cached.cache_clear()


# --- internals ---------------------------------------------------------


@lru_cache(maxsize=256)
def _load_cached(cache_key: tuple[str, str, str]) -> Any:
    """LRU-cached schema loader keyed by (resolved_target_root, capability, name)."""
    target_root_str, capability, name = cache_key
    target_root = Path(target_root_str)
    yaml_path = schemas_home(target_root, capability) / f"{name}.yaml"
    if not yaml_path.is_file():
        raise SchemaLookupError(
            f"{owner_label(capability)} schema {name!r}: YAML file {yaml_path} not found."
        )
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SchemaLookupError(
            f"{owner_label(capability)} schema {name!r}: could not read {yaml_path}: {exc}."
        ) from exc
    try:
        data = _yaml.load(text)
    except Exception as exc:  # ruamel.yaml raises various YAMLError subclasses
        raise SchemaLookupError(
            f"{owner_label(capability)} schema {name!r}: YAML parse error: {exc}."
        ) from exc
    return _stringify_dates(data)


def _find_owner_for_namespace(target_root: Path, namespace: str) -> str | None:
    """Walk every schemas home looking for the owner of `namespace`.

    A home owns the namespace if it contains `<namespace>.schema.json`
    declaring `x-pkit-id-collection` or `x-pkit-entry-id`. A declaration
    that does not read cleanly still claims the namespace, so the reader
    that follows reports what is wrong with it. Homes are visited in
    `iter_schema_homes` order (the core area, then capabilities sorted), so
    the first match is deterministic; None if no home matches.
    """
    for owner, schemas_dir in iter_schema_homes(target_root):
        companion = schemas_dir / f"{namespace}.schema.json"
        if not companion.is_file():
            continue
        try:
            schema = json.loads(companion.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if namespace_ownership(schema) is not None:
            return owner
    return None
