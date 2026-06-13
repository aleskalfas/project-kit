"""Authoring operations for the schemas mechanism.

Houses the write-side helpers that add entries to existing schemas or
stamp new ones. The validate-side (`schemas_validate.py`) and read-side
(`schemas.py`) modules are separate; this one is where data on disk
changes.

- `add_entry_to_namespace` appends one entry to a namespace owner's id
  collection. Round-trips the YAML via `ruamel.yaml`'s rt mode so
  existing comments and formatting survive. Validates after the write;
  restores the prior file on validation failure so partial mutations
  never linger.

- `stamp_new_schema` scaffolds a new YAML + JSON Schema companion pair
  under a capability's `schemas/` directory. Stamps the envelope, an
  empty collection, and the `x-pkit-id-collection` annotation pointing
  at it. Validates the stamp; rolls back if anything fails.

- `rename_entry` renames an entry id across the schemas mechanism:
  the namespace owner's collection key, every `[<namespace>:<old>]`
  typed token in any YAML under capabilities, and every mapping-key
  reference in fields whose companion declares
  `x-pkit-keys-from-namespace: <namespace>`. Validates everything;
  rolls back all changes on any failure.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ruamel.yaml import YAML

from project_kit.schemas import find_namespace_owner
from project_kit.schemas_validate import (
    _ID_COLLECTION_ANNOTATION,
    _resolve_json_pointer,
    validate_path,
)


CollectionForm = Literal["mapping", "list"]


_KEBAB_CASE = re.compile(r"^[a-z][a-z0-9-]*$")


class SchemaAuthoringError(Exception):
    """Raised when a schema-authoring operation fails to apply cleanly."""


@dataclass(frozen=True)
class SchemaStampResult:
    """Result of stamping a new schema pair."""

    yaml_path: Path
    companion_path: Path


@dataclass(frozen=True)
class RenameChange:
    """One change made by `rename_entry` — where and what kind."""

    yaml_path: Path
    kind: str  # "owner-key" | "token" | "annotation-key"
    detail: str  # human-readable description of the specific change


@dataclass(frozen=True)
class RenameResult:
    """Result of a `rename_entry` operation."""

    namespace: str
    old_id: str
    new_id: str
    changes: tuple[RenameChange, ...]


def add_entry_to_namespace(
    target_root: Path,
    namespace: str,
    entry_id: str,
    entry_data: dict[str, Any],
) -> Path:
    """Append a new entry to a namespace owner's id collection.

    Locates the namespace owner via `find_namespace_owner`, reads the
    YAML with round-trip preservation (comments + formatting + key
    order), appends the new entry to whichever collection shape the
    schema uses (mapping or list-of-objects-with-id), writes back, and
    re-validates. On validation failure, the file is restored to its
    prior state and `SchemaAuthoringError` is raised.

    `entry_id` must be kebab-case (`^[a-z][a-z0-9-]*$`). `entry_data` is
    a mapping of fields to values; for list-form collections, `id` is
    inserted as the first field. The companion JSON Schema's per-entry
    shape governs which fields are required + their types; validation
    catches violations.

    Returns the YAML file path. Raises:

    - `SchemaAuthoringError` if the namespace doesn't exist, the entry
      id collides with an existing one, or the resulting file fails
      validation.
    """
    capability = find_namespace_owner(target_root, namespace)
    if capability is None:
        raise SchemaAuthoringError(
            f"namespace {namespace!r} not found among installed capabilities."
        )

    capability_dir = target_root / ".pkit" / "capabilities" / capability / "schemas"
    yaml_path = capability_dir / f"{namespace}.yaml"
    companion_path = capability_dir / f"{namespace}.schema.json"

    schema = json.loads(companion_path.read_text(encoding="utf-8"))
    pointer = schema[_ID_COLLECTION_ANNOTATION]

    rt_yaml = YAML(typ="rt")
    rt_yaml.preserve_quotes = True
    rt_yaml.indent(mapping=2, sequence=4, offset=2)

    original = yaml_path.read_text(encoding="utf-8")
    with yaml_path.open("r", encoding="utf-8") as f:
        data = rt_yaml.load(f)

    try:
        collection = _resolve_json_pointer(data, pointer)
    except (KeyError, ValueError) as exc:
        raise SchemaAuthoringError(
            f"namespace {namespace!r}: {_ID_COLLECTION_ANNOTATION} pointer "
            f"{pointer!r} did not resolve in the YAML: {exc}."
        ) from exc

    if isinstance(collection, dict):
        if entry_id in collection:
            raise SchemaAuthoringError(
                f"id {entry_id!r} already exists in namespace {namespace!r}. "
                f"Use a different id, or edit the existing entry directly."
            )
        collection[entry_id] = entry_data
    elif isinstance(collection, list):
        existing_ids = [
            item.get("id")
            for item in collection
            if isinstance(item, dict) and "id" in item
        ]
        if entry_id in existing_ids:
            raise SchemaAuthoringError(
                f"id {entry_id!r} already exists in namespace {namespace!r}. "
                f"Use a different id, or edit the existing entry directly."
            )
        # For list-form collections, the new item's first field is its id.
        new_item: dict[str, Any] = {"id": entry_id, **entry_data}
        collection.append(new_item)
    else:
        raise SchemaAuthoringError(
            f"namespace {namespace!r}: collection at {pointer!r} is "
            f"{type(collection).__name__}; expected mapping or list-of-objects."
        )

    # Write the modified YAML.
    with yaml_path.open("w", encoding="utf-8") as f:
        rt_yaml.dump(data, f)

    # Re-validate. If anything's wrong (e.g., missing required fields,
    # invalid token reference), restore the original.
    report = validate_path(yaml_path, target_root=target_root)
    if not report.is_clean:
        yaml_path.write_text(original, encoding="utf-8")
        lines = "\n".join(f"  {i.location}\n    → {i.message}" for i in report.issues)
        raise SchemaAuthoringError(
            f"the new entry would fail validation; original file restored.\n"
            f"Issues:\n{lines}"
        )

    return yaml_path


def load_entry_data(source: Path | None) -> dict[str, Any]:
    """Read entry data from a file path or stdin.

    `source` is a Path to a YAML / JSON file, or None to read from stdin.
    YAML and JSON are both accepted (YAML is a superset). Returns the
    parsed mapping.

    Raises `SchemaAuthoringError` if the input isn't a mapping or fails
    to parse.
    """
    import sys

    if source is None or str(source) == "-":
        text = sys.stdin.read()
        origin_label = "<stdin>"
    else:
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise SchemaAuthoringError(f"could not read {source}: {exc}") from exc
        origin_label = str(source)

    rt_yaml = YAML(typ="safe")
    try:
        data = rt_yaml.load(text)
    except Exception as exc:  # ruamel.yaml has multiple error subclasses
        raise SchemaAuthoringError(
            f"could not parse entry data from {origin_label}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise SchemaAuthoringError(
            f"entry data from {origin_label} is "
            f"{type(data).__name__}; expected a mapping (YAML object)."
        )
    return data


# --- stamping a new schema --------------------------------------------


_MAPPING_YAML_TEMPLATE = """\
# <ONE-LINE DESCRIPTION OF WHAT THIS SCHEMA ENCODES>
#
# <PROSE EXPLAINING THE NAMESPACE'S PURPOSE — when each entry applies,
# what fields express, how the engine consumes them.>

schema_version: 1

# Optional source block. Uncomment when the schema distills from an
# external spec (per the .pkit/schemas/ area's YAML conventions).
# source:
#   upstream: <project-name>
#   commit: <40-char SHA>
#   decisions: [<external-decision-id>]
#   captured_at: YYYY-MM-DD

# Entries. Lookup by id.
#
# Per-entry fields (declare in the companion's $defs.entry.properties):
#   <FIELD>: <PROSE DESCRIPTION>
{collection}: {{}}
"""

_LIST_YAML_TEMPLATE = """\
# <ONE-LINE DESCRIPTION OF WHAT THIS SCHEMA ENCODES>
#
# <PROSE EXPLAINING THE NAMESPACE'S PURPOSE — when each entry applies,
# what fields express, how the engine consumes them.>

schema_version: 1

# Optional source block. Uncomment when the schema distills from an
# external spec.
# source:
#   upstream: <project-name>
#   commit: <40-char SHA>
#   decisions: [<external-decision-id>]
#   captured_at: YYYY-MM-DD

# Entries. Each item carries its `id:` first; remaining per-entry
# fields are declared in the companion's $defs.entry.properties.
{collection}: []
"""

_DOCUMENT_YAML_TEMPLATE = """\
# <ONE-LINE DESCRIPTION OF WHAT THIS DOCUMENT ENCODES>
#
# <PROSE EXPLAINING THE DOCUMENT'S PURPOSE — what this resource
# describes, which fields it carries, how the engine consumes it.
# This is a single-document schema: the file IS the resource, not a
# collection of entries. Declare the document's top-level fields in
# the companion's `properties`, then fill them in below.>

schema_version: 1

# Optional source block. Uncomment when the schema distills from an
# external spec (per the .pkit/schemas/ area's YAML conventions).
# source:
#   upstream: <project-name>
#   commit: <40-char SHA>
#   decisions: [<external-decision-id>]
#   captured_at: YYYY-MM-DD

# Top-level fields. Add them here once declared in the companion's
# `properties`. Example:
#
#   slug: example-slug
#   title: Human-readable label
"""


def stamp_new_schema(
    target_root: Path,
    capability: str,
    name: str,
    *,
    collection_form: CollectionForm = "mapping",
    collection_name: str = "entries",
    no_namespace: bool = False,
) -> SchemaStampResult:
    """Stamp a new YAML + JSON Schema companion pair under a capability's `schemas/`.

    `capability` is the target: the reserved value `core` stamps into the
    core schemas area (`.pkit/schemas/`); any other value names a capability
    under `.pkit/capabilities/<capability>/schemas/`.

    `name` is the schema's filename stem (e.g., `issue-types`,
    `validation-severity`, `trip`).

    Two stamp shapes:

    - **Namespace owner** (default). Top-level collection of id-keyed
      entries; companion carries `x-pkit-id-collection`. `collection_name`
      is the top-level YAML key holding the id collection (e.g.,
      `types`, `severities`, `entries`); `collection_form` chooses
      between mapping (keys are ids) and list-of-objects (each item has
      `id:`).

    - **Document** (`no_namespace=True`). One resource per file; no
      top-level collection, no `x-pkit-id-collection`. The YAML carries
      the document's top-level fields directly; the companion's
      `properties` declares their shape. `collection_form` and
      `collection_name` are ignored on the document path.

    The stamp writes:

    - `<name>.yaml` with the envelope (`schema_version`, optional
      `source` block) + the appropriate body for the chosen shape +
      leading prose-placeholder comments.
    - `<name>.schema.json` with the envelope. For the namespace-owner
      path, includes `x-pkit-id-collection` + a placeholder `$defs.entry`.
      For the document path, includes a flat `properties: {}` placeholder
      with no collection annotation.

    Re-validates the stamp via `validate_path`. On failure, removes
    both files and raises `SchemaAuthoringError`.
    """
    if not _KEBAB_CASE.match(name):
        raise SchemaAuthoringError(
            f"namespace name {name!r} must be kebab-case "
            f"(matching `^[a-z][a-z0-9-]*$`)."
        )
    if not no_namespace and not _KEBAB_CASE.match(collection_name):
        raise SchemaAuthoringError(
            f"collection name {collection_name!r} must be kebab-case "
            f"(matching `^[a-z][a-z0-9-]*$`)."
        )

    # `core` is the reserved target for the core schemas area (.pkit/schemas/);
    # any other value names a capability under .pkit/capabilities/<cap>/schemas/.
    if capability == "core":
        schemas_dir = target_root / ".pkit" / "schemas"
        if not schemas_dir.is_dir():
            raise SchemaAuthoringError(
                f"core schemas area not found at {schemas_dir} — expected "
                f".pkit/schemas/ in this project tree."
            )
    else:
        capability_dir = target_root / ".pkit" / "capabilities" / capability
        if not capability_dir.is_dir():
            raise SchemaAuthoringError(
                f"capability {capability!r} not found at "
                f"{capability_dir.relative_to(target_root) if target_root in capability_dir.parents or capability_dir == target_root else capability_dir}. "
                f"Create the capability first via `pkit new capability`."
            )
        schemas_dir = capability_dir / "schemas"
        schemas_dir.mkdir(exist_ok=True)

    yaml_path = schemas_dir / f"{name}.yaml"
    companion_path = schemas_dir / f"{name}.schema.json"

    if yaml_path.exists() or companion_path.exists():
        location = "the core schemas area" if capability == "core" else f"capability {capability!r}"
        raise SchemaAuthoringError(
            f"schema {name!r} already exists in {location}. "
            f"Edit the existing files, or pick a different name."
        )

    # Stamp the YAML envelope.
    if no_namespace:
        yaml_path.write_text(_DOCUMENT_YAML_TEMPLATE, encoding="utf-8")
    else:
        template = (
            _MAPPING_YAML_TEMPLATE if collection_form == "mapping" else _LIST_YAML_TEMPLATE
        )
        yaml_path.write_text(template.format(collection=collection_name), encoding="utf-8")

    # Stamp the companion. Use ensure_ascii=False so unicode (em-dashes,
    # etc.) appear literally — matches the kit's existing companions.
    if no_namespace:
        companion = _build_document_companion(name)
    else:
        companion = _build_companion(name, collection_name, collection_form)
    companion_path.write_text(
        json.dumps(companion, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Validate the stamp. On any issue, roll back both files.
    report = validate_path(yaml_path, target_root=target_root)
    if not report.is_clean:
        yaml_path.unlink(missing_ok=True)
        companion_path.unlink(missing_ok=True)
        lines = "\n".join(f"  {i.location}\n    → {i.message}" for i in report.issues)
        raise SchemaAuthoringError(
            f"stamped schema failed validation; both files removed.\n{lines}"
        )

    return SchemaStampResult(yaml_path=yaml_path, companion_path=companion_path)


def _build_companion(
    name: str, collection_name: str, collection_form: CollectionForm
) -> dict[str, Any]:
    """Construct the JSON Schema companion dict for a new schema."""
    pointer = f"/{collection_name}"
    base: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{name}.schema.json",
        "title": f"<TITLE — short label for what {name} encodes>",
        "description": (
            f"Formal shape of {name}.yaml — <ONE-PARAGRAPH DESCRIPTION>. "
            f"Companion per COR-018 / the .pkit/schemas/ area conventions."
        ),
        "x-pkit-id-collection": pointer,
        "type": "object",
        "required": ["schema_version", collection_name],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "source": {"$ref": "refs.schema.json#/$defs/source"},
        },
        "$defs": {},
    }
    if collection_form == "mapping":
        base["properties"][collection_name] = {
            "type": "object",
            "patternProperties": {"^[a-z][a-z0-9-]*$": {"$ref": "#/$defs/entry"}},
            "additionalProperties": False,
            "description": (
                "Entries. Keys are kebab-case ids; values match $defs.entry."
            ),
        }
        base["$defs"]["entry"] = {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
            "description": (
                "Per-entry shape. Declare each field's type and constraints here "
                "before adding entries via `pkit schemas add`."
            ),
        }
    else:  # list form
        base["properties"][collection_name] = {
            "type": "array",
            "items": {"$ref": "#/$defs/entry"},
            "description": (
                "Entries. Each item has `id:` first (kebab-case); remaining "
                "fields match $defs.entry."
            ),
        }
        base["$defs"]["entry"] = {
            "type": "object",
            "required": ["id"],
            "additionalProperties": False,
            "properties": {
                "id": {"type": "string", "pattern": "^[a-z][a-z0-9-]*$"},
            },
            "description": (
                "Per-entry shape. Declare additional fields' types and "
                "constraints here before adding entries via `pkit schemas add`."
            ),
        }
    return base


def _build_document_companion(name: str) -> dict[str, Any]:
    """Construct the JSON Schema companion dict for a document-shaped schema.

    Document schemas describe one resource per file. The companion has
    no `x-pkit-id-collection` (no namespace membership) and no narrowed
    `<name>_ref` `$defs` entry by default — the document IS the resource,
    not a member of a namespace. Top-level `properties` is left empty for
    the author to fill in.
    """
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{name}.schema.json",
        "title": f"<TITLE — short label for what {name} encodes>",
        "description": (
            f"Formal shape of {name}.yaml — <ONE-PARAGRAPH DESCRIPTION>. "
            f"Document-shaped schema: the file IS the resource (no top-level "
            f"id collection). Companion per COR-018 / the .pkit/schemas/ "
            f"area conventions."
        ),
        "type": "object",
        "required": ["schema_version"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "source": {"$ref": "refs.schema.json#/$defs/source"},
        },
    }


# --- renaming an entry id --------------------------------------------


def rename_entry(
    target_root: Path,
    namespace: str,
    old_id: str,
    new_id: str,
) -> RenameResult:
    """Rename an entry id across the schemas mechanism.

    Updates three classes of reference, in order:

    1. The namespace owner's collection — mapping form: rename the key;
       list form: update the `id:` field of the matching item.
    2. Every value-position typed token `[<namespace>:<old_id>]` in any
       YAML under installed capabilities.
    3. Every mapping-key reference in fields whose companion declares
       `x-pkit-keys-from-namespace: <namespace>`.

    After all rewrites, re-validates every affected file. If any
    validation fails, restores all files from backup and raises
    `SchemaAuthoringError`.

    Raises `SchemaAuthoringError` if `new_id` isn't kebab-case, isn't
    different from `old_id`, the namespace doesn't exist, `old_id`
    isn't present in the namespace, or `new_id` already is.
    """
    if not _KEBAB_CASE.match(new_id):
        raise SchemaAuthoringError(
            f"new id {new_id!r} must be kebab-case "
            f"(matching `^[a-z][a-z0-9-]*$`)."
        )
    if new_id == old_id:
        raise SchemaAuthoringError(
            f"new id {new_id!r} is identical to old id; nothing to rename."
        )

    capability = find_namespace_owner(target_root, namespace)
    if capability is None:
        raise SchemaAuthoringError(
            f"namespace {namespace!r} not found among installed capabilities."
        )

    capabilities_dir = target_root / ".pkit" / "capabilities"
    owner_yaml = (
        capabilities_dir / capability / "schemas" / f"{namespace}.yaml"
    )
    owner_companion = owner_yaml.with_suffix(".schema.json")

    # Discover every YAML across capabilities (used for token + key scans).
    all_yamls = sorted(capabilities_dir.glob("*/schemas/*.yaml"))

    # Take backups of every file we'll touch. We rewrite under a backup
    # → write → validate → (rollback-on-fail) flow.
    backups: dict[Path, str] = {p: p.read_text(encoding="utf-8") for p in all_yamls}

    try:
        changes: list[RenameChange] = []

        # Step 1: Update the namespace owner's collection.
        owner_change = _rename_owner_entry(
            owner_yaml, owner_companion, namespace, old_id, new_id
        )
        if owner_change is None:
            raise SchemaAuthoringError(
                f"id {old_id!r} not found in namespace {namespace!r}."
            )
        changes.append(owner_change)

        # Step 2: Update value-position typed tokens.
        token_old = f"[{namespace}:{old_id}]"
        token_new = f"[{namespace}:{new_id}]"
        for yaml_path in all_yamls:
            text = yaml_path.read_text(encoding="utf-8")
            if token_old not in text:
                continue
            count = text.count(token_old)
            yaml_path.write_text(text.replace(token_old, token_new), encoding="utf-8")
            changes.append(
                RenameChange(
                    yaml_path=yaml_path,
                    kind="token",
                    detail=f"replaced {count} occurrence(s) of {token_old!r} with {token_new!r}",
                )
            )

        # Step 3: Update annotation-based key references. For each
        # companion whose `x-pkit-keys-from-namespace` points at our
        # namespace, find the data path and rename old_id → new_id in
        # the YAML's mapping at that path.
        all_companions = sorted(capabilities_dir.glob("*/schemas/*.schema.json"))
        for companion_path in all_companions:
            try:
                schema = json.loads(companion_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            paths = list(_walk_keys_from_namespace_for_renames(schema, namespace))
            if not paths:
                continue
            yaml_path = companion_path.parent / (
                companion_path.name.removesuffix(".schema.json") + ".yaml"
            )
            if not yaml_path.is_file():
                continue
            for data_path in paths:
                change = _rename_annotated_key(
                    yaml_path, data_path, old_id, new_id, namespace
                )
                if change is not None:
                    changes.append(change)

        # Validate every affected file.
        affected = {c.yaml_path for c in changes}
        for yaml_path in affected:
            report = validate_path(yaml_path, target_root=target_root)
            if not report.is_clean:
                lines = "\n".join(
                    f"  {i.location}\n    → {i.message}" for i in report.issues
                )
                raise SchemaAuthoringError(
                    f"rename caused validation failure in {yaml_path.relative_to(target_root)}; "
                    f"all changes rolled back.\n{lines}"
                )

    except Exception:
        # Roll back every file we touched.
        for path, text in backups.items():
            if path.read_text(encoding="utf-8") != text:
                path.write_text(text, encoding="utf-8")
        raise

    return RenameResult(
        namespace=namespace,
        old_id=old_id,
        new_id=new_id,
        changes=tuple(changes),
    )


def _rename_owner_entry(
    yaml_path: Path,
    companion_path: Path,
    namespace: str,
    old_id: str,
    new_id: str,
) -> RenameChange | None:
    """Rename the entry's key/id in the namespace owner's YAML.

    Returns the change description or None if `old_id` isn't present.
    Raises `SchemaAuthoringError` if `new_id` is already present.
    """
    schema = json.loads(companion_path.read_text(encoding="utf-8"))
    pointer = schema[_ID_COLLECTION_ANNOTATION]

    rt_yaml = YAML(typ="rt")
    rt_yaml.preserve_quotes = True
    rt_yaml.indent(mapping=2, sequence=4, offset=2)
    with yaml_path.open("r", encoding="utf-8") as f:
        data = rt_yaml.load(f)
    collection = _resolve_json_pointer(data, pointer)

    if isinstance(collection, dict):
        if old_id not in collection:
            return None
        if new_id in collection:
            raise SchemaAuthoringError(
                f"new id {new_id!r} already exists in namespace {namespace!r}."
            )
        # Rebuild the mapping with the renamed key to preserve order.
        items = list(collection.items())
        collection.clear()
        for key, value in items:
            collection[new_id if key == old_id else key] = value
    elif isinstance(collection, list):
        target_idx = None
        for idx, item in enumerate(collection):
            if isinstance(item, dict) and item.get("id") == old_id:
                target_idx = idx
            if isinstance(item, dict) and item.get("id") == new_id:
                raise SchemaAuthoringError(
                    f"new id {new_id!r} already exists in namespace {namespace!r}."
                )
        if target_idx is None:
            return None
        collection[target_idx]["id"] = new_id
    else:
        raise SchemaAuthoringError(
            f"namespace {namespace!r}: collection at {pointer!r} is "
            f"{type(collection).__name__}; expected mapping or list-of-objects."
        )

    with yaml_path.open("w", encoding="utf-8") as f:
        rt_yaml.dump(data, f)

    return RenameChange(
        yaml_path=yaml_path,
        kind="owner-key",
        detail=f"renamed {old_id!r} → {new_id!r} in namespace owner",
    )


def _walk_keys_from_namespace_for_renames(
    schema: Any, target_namespace: str, data_pointer: tuple[str, ...] = ()
) -> Any:
    """Walk a schema, yield data paths where keys belong to `target_namespace`.

    Mirrors `schemas_validate._walk_keys_from_namespace` but filters to
    one namespace and yields only the path (not the namespace).
    """
    if not isinstance(schema, dict):
        return
    ns = schema.get("x-pkit-keys-from-namespace")
    if isinstance(ns, str) and ns == target_namespace:
        yield data_pointer
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for prop_name, prop_schema in properties.items():
            yield from _walk_keys_from_namespace_for_renames(
                prop_schema, target_namespace, data_pointer + (prop_name,)
            )


def _rename_annotated_key(
    yaml_path: Path,
    data_path: tuple[str, ...],
    old_id: str,
    new_id: str,
    namespace: str,
) -> RenameChange | None:
    """Rename a bare key in an annotation-tracked mapping.

    Returns the change or None if the key isn't present at that data path.
    Raises `SchemaAuthoringError` if `new_id` is already a key.
    """
    rt_yaml = YAML(typ="rt")
    rt_yaml.preserve_quotes = True
    rt_yaml.indent(mapping=2, sequence=4, offset=2)
    with yaml_path.open("r", encoding="utf-8") as f:
        data = rt_yaml.load(f)

    node: Any = data
    for part in data_path:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    if not isinstance(node, dict):
        return None
    if old_id not in node:
        return None
    if new_id in node:
        raise SchemaAuthoringError(
            f"in {yaml_path.name}: new key {new_id!r} already present at "
            f"/{'/'.join(data_path)}; would collide with rename of {old_id!r}."
        )
    # Rebuild to preserve insertion order.
    items = list(node.items())
    node.clear()
    for key, value in items:
        node[new_id if key == old_id else key] = value

    with yaml_path.open("w", encoding="utf-8") as f:
        rt_yaml.dump(data, f)

    return RenameChange(
        yaml_path=yaml_path,
        kind="annotation-key",
        detail=f"renamed bare key {old_id!r} → {new_id!r} at /{'/'.join(data_path)} "
        f"(validated against namespace {namespace!r} via x-pkit-keys-from-namespace)",
    )
