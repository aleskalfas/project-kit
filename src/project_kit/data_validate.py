"""Adopter-data validation against capability schemas (per COR-023).

Where `schemas_validate.py` validates *capability-side schema pairs* (the
spec: YAML + JSON Schema companion), this module validates *adopter-side
data files* against those schemas. The binding from data file to schema
is resolved in two steps per COR-023 (superseding COR-022's separate
`bindings.yaml` registry):

1. **Field-first.** If the data file carries a top-level
   `pkit_schema: <capability>:<schema>` field, that's the binding.
2. **Capability fallback.** Otherwise, walk every installed capability's
   `schemas/*.yaml`; for each schema with a `binds_to:` field, match
   the file's repo-relative path against each glob. First match wins;
   multiple matches across capabilities surface as ambiguous.

Schema-version cross-check: if the data file's `schema_version` does
not match the resolved schema's `schema_version`, validation refuses
with a structured migration hint. Auto-migration is out of scope in v1.

The CLI surface is `pkit data validate <path>` — accepts a file or
directory, walks YAML files in directories recursively, prints findings,
exits non-zero on any failure. Distinct from `pkit schemas validate`
which validates capability schema pairs.
"""

from __future__ import annotations

import fnmatch
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import click
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing.exceptions import Unresolvable
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit.manifest import read_backbone_manifest
from project_kit.schemas_validate import (
    _ID_COLLECTION_ANNOTATION,
    _TOKEN_PATTERN,
    _build_registry_for_paths,
    _collect_ids,
    _resolve_json_pointer,
    _stringify_dates,
)

_yaml = YAML(typ="safe")

# The top-level field by which an adopter data file declares its schema.
# Per COR-023, the value is the bare two-part form `<capability>:<schema>`,
# distinct from COR-019's bracketed `[<namespace>:<id>]` token.
PKIT_SCHEMA_FIELD = "pkit_schema"

# The top-level field on a capability schema YAML declaring path-pattern
# fallbacks for adopter data files that omit the `pkit_schema:` field.
# Per COR-023.
BINDS_TO_FIELD = "binds_to"

# The value-position companion annotation that marks a field as holding
# typed references (per COR-029). Its value is the namespace the field's
# tokens must resolve into. It is a *position-gate*: the cross-file
# reference resolver inspects only fields the schema author annotated,
# so incidental bracketed tokens in free-text fields are out of scope by
# construction. The symmetric counterpart to COR-019's key-position
# `x-pkit-keys-from-namespace`.
REFERENCE_NAMESPACE_ANNOTATION = "x-pkit-reference-namespace"


BindingSource = Literal["field", "capability-binding"]
Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class ResolvedBinding:
    """A successfully-resolved binding from data file to schema."""

    data_path: Path
    capability: str
    schema_name: str
    schema_yaml: Path  # path to the capability's <schema>.yaml
    companion: Path  # path to <schema>.schema.json
    source: BindingSource  # how the binding was resolved


@dataclass(frozen=True)
class BindingError:
    """A failed binding resolution."""

    data_path: Path
    message: str


@dataclass(frozen=True)
class DataValidationIssue:
    """One finding from data validation.

    `severity` distinguishes a hard failure (`"error"` — shape violation,
    dangling reference, duplicate id; fails the run) from a soft advisory
    (`"warning"` — a reference whose namespace has no bound file anywhere
    in scope, a routine in-progress state per COR-029; reported, does not
    fail the run). Defaults to `"error"` so every existing call site keeps
    its hard-failure semantics.
    """

    location: str  # path-relative-to-target or "<path>:<json-pointer>"
    message: str
    severity: Severity = "error"


@dataclass(frozen=True)
class DataValidationReport:
    """Outcome of validating one or more adopter data files."""

    files_checked: int = 0
    issues: tuple[DataValidationIssue, ...] = field(default_factory=tuple)

    @property
    def is_clean(self) -> bool:
        """True iff there are no findings at all (errors or warnings)."""
        return not self.issues

    @property
    def errors(self) -> tuple[DataValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[DataValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")

    @property
    def has_errors(self) -> bool:
        """True iff any hard-failure finding is present (the exit gate)."""
        return any(i.severity == "error" for i in self.issues)


@dataclass(frozen=True)
class CapabilityBindings:
    """A capability's loaded `binds_to:` entries, collected across its schemas.

    Aggregates the `binds_to:` patterns declared inside each schema YAML
    under `<capability>/schemas/*.yaml`. The aggregate keeps the per-
    capability granularity the resolver needs (first match within a
    capability wins; multiple across capabilities are ambiguous).
    """

    capability: str
    # Each binding as (schema-stem, glob-pattern).
    entries: tuple[tuple[str, str], ...]


# --- binding resolution -------------------------------------------------


def discover_data_files(path: Path) -> list[Path]:
    """Resolve a file or directory argument to the list of YAML files to validate.

    Files return a one-element list (regardless of extension; we trust the
    caller's intent). Directories walk recursively for `*.yaml`. The
    walk skips `.pkit/` subtrees — those are kit-managed, not adopter
    data — and any sidecar `*.schema.json` files.
    """
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    out: list[Path] = []
    for yaml_path in sorted(path.rglob("*.yaml")):
        # Skip kit-managed trees (capability schemas, etc.).
        if ".pkit" in yaml_path.parts:
            continue
        if yaml_path.name.endswith(".schema.json"):
            continue
        out.append(yaml_path)
    return out


def resolve_binding(
    data_path: Path,
    target_root: Path,
    *,
    capability_bindings: list[CapabilityBindings] | None = None,
) -> ResolvedBinding | BindingError:
    """Resolve the schema binding for one adopter data file (per COR-022).

    Order:
    1. Parse the file; if it carries `pkit_schema: <capability>:<schema>`,
       resolve that.
    2. Otherwise, walk every installed capability's `schemas/*.yaml`;
       collect each schema's `binds_to:` patterns; use the first matching
       binding. Multiple matches across capabilities → ambiguous.
    3. Otherwise, no binding found.

    `capability_bindings`, if provided, is reused across multiple calls
    (avoids re-walking each capability's schemas per file).
    """
    # 1. Parse the YAML enough to inspect `pkit_schema`.
    try:
        data = _yaml.load(data_path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        return BindingError(
            data_path=data_path,
            message=f"YAML parse error: {exc}",
        )
    except OSError as exc:
        return BindingError(
            data_path=data_path,
            message=f"could not read data file: {exc}",
        )

    # Empty or non-mapping top-level — proceed to capability fallback.
    field_value: str | None = None
    if isinstance(data, dict):
        raw_value = data.get(PKIT_SCHEMA_FIELD)
        if raw_value is not None:
            if not isinstance(raw_value, str):
                return BindingError(
                    data_path=data_path,
                    message=f"{PKIT_SCHEMA_FIELD!r} value must be a string of the form "
                    f"`<capability>:<schema>` (got {type(raw_value).__name__}).",
                )
            field_value = raw_value

    if field_value is not None:
        return _resolve_from_field(data_path, target_root, field_value)

    # 2. Capability-binding fallback.
    if capability_bindings is None:
        capability_bindings = load_all_capability_bindings(target_root)

    matches = _match_bindings(data_path, target_root, capability_bindings)
    if len(matches) == 1:
        cap_name, schema_name = matches[0]
        return _build_binding(
            data_path, target_root, cap_name, schema_name, source="capability-binding"
        )
    if len(matches) > 1:
        match_list = ", ".join(f"{c}:{s}" for c, s in matches)
        return BindingError(
            data_path=data_path,
            message=(
                f"ambiguous binding: file matches multiple capability bindings ({match_list}). "
                f"Add a top-level `{PKIT_SCHEMA_FIELD}: <capability>:<schema>` field "
                f"to disambiguate."
            ),
        )

    # 3. Nothing resolved.
    return BindingError(
        data_path=data_path,
        message=(
            f"no schema binding found for this file. Add a top-level "
            f"`{PKIT_SCHEMA_FIELD}: <capability>:<schema>` field, or declare a "
            f"`{BINDS_TO_FIELD}:` glob inside the capability's schema YAML."
        ),
    )


def _resolve_from_field(
    data_path: Path, target_root: Path, value: str
) -> ResolvedBinding | BindingError:
    """Resolve a `pkit_schema:` field value to a schema path."""
    parts = value.split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return BindingError(
            data_path=data_path,
            message=(
                f"{PKIT_SCHEMA_FIELD!r} value {value!r} is not the expected "
                f"`<capability>:<schema>` form."
            ),
        )
    capability, schema_name = parts
    return _build_binding(
        data_path, target_root, capability, schema_name, source="field"
    )


def _build_binding(
    data_path: Path,
    target_root: Path,
    capability: str,
    schema_name: str,
    *,
    source: BindingSource,
) -> ResolvedBinding | BindingError:
    """Materialise a ResolvedBinding by checking that the schema files exist."""
    cap_dir = target_root / ".pkit" / "capabilities" / capability
    if not cap_dir.is_dir():
        return BindingError(
            data_path=data_path,
            message=(
                f"capability {capability!r} is not installed at "
                f".pkit/capabilities/{capability}/."
            ),
        )
    schema_yaml = cap_dir / "schemas" / f"{schema_name}.yaml"
    companion = cap_dir / "schemas" / f"{schema_name}.schema.json"
    if not schema_yaml.is_file() or not companion.is_file():
        return BindingError(
            data_path=data_path,
            message=(
                f"schema {capability!r}:{schema_name!r} not found "
                f"(expected pair {schema_yaml.relative_to(target_root)} + "
                f"{companion.relative_to(target_root)})."
            ),
        )
    return ResolvedBinding(
        data_path=data_path,
        capability=capability,
        schema_name=schema_name,
        schema_yaml=schema_yaml,
        companion=companion,
        source=source,
    )


# --- capability binds_to: loading --------------------------------------


def load_all_capability_bindings(target_root: Path) -> list[CapabilityBindings]:
    """Aggregate `binds_to:` patterns from every installed capability's schemas.

    For each installed capability, walks `<capability>/schemas/*.yaml`
    (excluding companion `.schema.json` files) and collects each
    schema's `binds_to:` glob patterns. Capabilities with no schemas or
    no `binds_to:` declarations contribute an empty (or skipped) entry.

    Capabilities iterate in backbone-manifest order; within a capability,
    schemas iterate in lexicographic filename order; within a schema,
    `binds_to:` entries keep their declared order. The resolver collapses
    multi-pattern entries into the same `(schema, glob)` tuple list.
    """
    out: list[CapabilityBindings] = []
    backbone = read_backbone_manifest(target_root)
    cap_names: list[str] = []
    if backbone is not None:
        cap_names = [c.name for c in backbone.components if c.kind == "capability"]
    cap_names.sort()
    for name in cap_names:
        entries = _collect_binds_to_for_capability(target_root, name)
        if not entries:
            continue
        out.append(CapabilityBindings(capability=name, entries=tuple(entries)))
    return out


def _collect_binds_to_for_capability(
    target_root: Path, capability: str
) -> list[tuple[str, str]]:
    """Walk a capability's schemas/*.yaml and aggregate `binds_to:` entries.

    Returns a flat list of `(schema-stem, glob)` tuples. Schemas without
    `binds_to:` (most schemas in the kit are namespace owners or
    capability-internal) contribute nothing. Parse failures are silent —
    the resolver continues with whatever it can read.
    """
    schemas_dir = target_root / ".pkit" / "capabilities" / capability / "schemas"
    if not schemas_dir.is_dir():
        return []
    entries: list[tuple[str, str]] = []
    for schema_yaml in sorted(schemas_dir.glob("*.yaml")):
        # Skip companions and bindings.yaml leftovers (defensive).
        if schema_yaml.name.endswith(".schema.json"):
            continue
        binds = _read_binds_to(schema_yaml)
        if not binds:
            continue
        schema_stem = schema_yaml.stem
        for glob in binds:
            entries.append((schema_stem, glob))
    return entries


def _read_binds_to(schema_yaml: Path) -> list[str]:
    """Read `binds_to:` from a schema YAML. Returns a list of glob strings (empty if absent)."""
    try:
        raw = _yaml.load(schema_yaml.read_text(encoding="utf-8"))
    except (YAMLError, OSError):
        return []
    if not isinstance(raw, dict):
        return []
    value = raw.get(BINDS_TO_FIELD)
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            out.append(item)
    return out


def _match_bindings(
    data_path: Path,
    target_root: Path,
    capability_bindings: list[CapabilityBindings],
) -> list[tuple[str, str]]:
    """Return every (capability, schema-stem) pair whose glob matches the file."""
    try:
        rel = data_path.relative_to(target_root)
    except ValueError:
        rel = data_path
    rel_str = str(rel)
    matches: list[tuple[str, str]] = []
    for cap_bindings in capability_bindings:
        for schema_name, glob in cap_bindings.entries:
            if fnmatch.fnmatch(rel_str, glob):
                matches.append((cap_bindings.capability, schema_name))
                # First match within a capability is enough — no need to
                # walk further entries in the same capability for the
                # same file. Multi-capability ambiguity is what callers
                # care about.
                break
    return matches


# --- validation ---------------------------------------------------------


def validate_data_file(
    data_path: Path,
    target_root: Path,
    *,
    capability_bindings: list[CapabilityBindings] | None = None,
) -> list[DataValidationIssue]:
    """Resolve binding + run shape validation for one adopter data file.

    Two checks:
    - **Schema-version cross-check.** Refuses with a migration hint when
      the data file's `schema_version` differs from the resolved schema's
      `schema_version`.
    - **Shape.** Validates the data YAML against the resolved JSON Schema
      companion, just like `pkit schemas validate` does for capability
      schema pairs.

    Returns the findings (empty = clean).
    """
    binding = resolve_binding(
        data_path, target_root, capability_bindings=capability_bindings
    )
    rel = _rel(data_path, target_root)
    if isinstance(binding, BindingError):
        return [DataValidationIssue(location=rel, message=binding.message)]

    # Parse the data file again — same content the binding step parsed,
    # but resolve_binding returned only the binding, not the data.
    try:
        data = _yaml.load(data_path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        return [DataValidationIssue(location=rel, message=f"YAML parse error: {exc}")]
    data = _stringify_dates(data)

    # Load companion + run schema-version cross-check.
    try:
        companion_schema = json.loads(binding.companion.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [
            DataValidationIssue(
                location=_rel(binding.companion, target_root),
                message=(
                    f"companion is not valid JSON: {exc.msg} "
                    f"at line {exc.lineno} col {exc.colno}."
                ),
            )
        ]
    try:
        Draft202012Validator.check_schema(companion_schema)
    except SchemaError as exc:
        return [
            DataValidationIssue(
                location=_rel(binding.companion, target_root),
                message=f"companion is not a valid Draft 2020-12 JSON Schema: {exc.message}",
            )
        ]

    issues: list[DataValidationIssue] = []
    version_mismatch = _check_schema_version(binding, data, target_root, rel)
    if version_mismatch is not None:
        issues.append(version_mismatch)
        # Don't run shape validation against a mismatched schema — the
        # error semantics would be confusing. Refuse and surface the
        # migration hint as the only finding.
        return issues

    # Shape validation. Build a Registry covering sibling companions in
    # the capability's schemas/ dir (so $refs to namespace-owner
    # narrowed patterns resolve) + the kit-wide _defs library.
    schemas_dir = binding.companion.parent
    registry_paths = sorted(schemas_dir.glob("*.schema.json"))
    defs_dir = target_root / ".pkit" / "schemas" / "_defs"
    if defs_dir.is_dir():
        registry_paths.extend(sorted(defs_dir.glob("*.schema.json")))
    registry, registry_issues = _build_registry_for_paths(
        registry_paths, target_root, already_reported=set()
    )
    for ri in registry_issues:
        issues.append(DataValidationIssue(location=ri.location, message=ri.message))

    validator = Draft202012Validator(companion_schema, registry=registry)
    try:
        shape_errors = list(validator.iter_errors(data))
    except Unresolvable as exc:
        issues.append(
            DataValidationIssue(
                location=rel,
                message=f"cross-file $ref could not resolve: {exc.ref!r}.",
            )
        )
        shape_errors = []
    for error in sorted(shape_errors, key=lambda e: list(e.absolute_path)):
        pointer = (
            "/" + "/".join(str(p) for p in error.absolute_path)
            if error.absolute_path
            else ""
        )
        issues.append(
            DataValidationIssue(
                location=f"{rel}{pointer}",
                message=error.message,
            )
        )
    return issues


def _check_schema_version(
    binding: ResolvedBinding,
    data: Any,
    target_root: Path,
    data_rel: str,
) -> DataValidationIssue | None:
    """Compare data file's schema_version against the schema's. Refuse on mismatch."""
    data_version = data.get("schema_version") if isinstance(data, dict) else None
    schema_version = _read_schema_version(binding.schema_yaml)
    if data_version is None or schema_version is None:
        # If either is missing, defer to the shape pass to surface the
        # missing-required-field error.
        return None
    if data_version == schema_version:
        return None
    return DataValidationIssue(
        location=data_rel,
        message=(
            f"schema_version mismatch: data declares {data_version!r} but "
            f"{binding.capability}:{binding.schema_name} is at version "
            f"{schema_version!r}. Migrate the data (see the capability's "
            f"migration tier, per COR-010 + COR-017), or pin the capability "
            f"to the data's version. Auto-migration is not supported in v1 "
            f"per COR-023."
        ),
    )


def _read_schema_version(schema_yaml: Path) -> int | None:
    """Read `schema_version` from the capability schema's YAML. Returns None if unreadable."""
    try:
        raw = _yaml.load(schema_yaml.read_text(encoding="utf-8"))
    except (YAMLError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    val = raw.get("schema_version")
    if isinstance(val, int):
        return val
    return None


def _rel(path: Path, target_root: Path | None) -> str:
    """Render a path relative to target_root when possible; otherwise absolute."""
    if target_root is None:
        return str(path)
    try:
        return str(path.relative_to(target_root))
    except ValueError:
        return str(path)


# --- cross-file reference resolution (per COR-029) ----------------------
#
# Scope-subtree resolution: the id pool for a namespace is the *union* of
# every in-scope file bound to that namespace, read through each schema's
# `x-pkit-id-collection` (resolving "through the binding to the bound
# instance", not into the namespace schema's own empty collection). A
# reference resolves iff its id is in that pool. Isolation is by what you
# validate — a narrower target is a stricter universe. Position-gated: only
# fields the citing schema marks `x-pkit-reference-namespace` are inspected.


@dataclass(frozen=True)
class _NsPool:
    """The id pool for one (capability, namespace) within the validation scope.

    Either resolvable (`ids` is the union across bound instance files) or
    in error (`error` explains why the namespace can't supply a pool —
    e.g. its companion declares no `x-pkit-id-collection`).
    """

    ids: frozenset[str] = frozenset()
    error: str | None = None


def _companion_json(path: Path, cache: dict[Path, Any]) -> Any:
    """Load + cache a companion JSON document. Returns None if unreadable."""
    if path in cache:
        return cache[path]
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = None
    cache[path] = doc
    return doc


def _resolve_ref(
    ref: str, companion_path: Path, schemas_dir: Path, cache: dict[Path, Any]
) -> tuple[Any, Path] | None:
    """Resolve a JSON Schema `$ref` to (subschema, owning-companion-path).

    Handles intra-file `#/$defs/x`, sibling-companion `other.schema.json#/$defs/x`,
    and bare `other.schema.json`. Sibling refs resolve within the citing
    schema's own `schemas/` directory (the kit convention). Returns None
    when the target can't be loaded or located.
    """
    file_part, _, frag = ref.partition("#")
    target_companion = companion_path if file_part == "" else schemas_dir / file_part
    doc = _companion_json(target_companion, cache)
    if doc is None:
        return None
    if frag in ("", "/"):
        return doc, target_companion
    try:
        sub = _resolve_json_pointer(doc, frag)
    except (KeyError, ValueError):
        return None
    return sub, target_companion


def _collect_reference_checks(
    schema: Any,
    data: Any,
    *,
    companion_path: Path,
    schemas_dir: Path,
    cache: dict[Path, Any],
    pointer: str,
    visited: frozenset[tuple[Path, str]],
) -> Iterator[tuple[str, Any, str]]:
    """Co-walk a companion (sub)schema and the data under it.

    Yields `(namespace, value, json-pointer)` for every data position that
    sits under an `x-pkit-reference-namespace` annotation — following
    `properties`, `items`, `$ref` (intra- and cross-file), and
    `allOf`/`anyOf`/`oneOf`. `$ref` cycles are guarded by `visited`.
    """
    if not isinstance(schema, dict):
        return
    ref = schema.get("$ref")
    if isinstance(ref, str):
        vkey = (companion_path, ref)
        if vkey not in visited:
            resolved = _resolve_ref(ref, companion_path, schemas_dir, cache)
            if resolved is not None:
                sub_schema, sub_companion = resolved
                yield from _collect_reference_checks(
                    sub_schema,
                    data,
                    companion_path=sub_companion,
                    schemas_dir=schemas_dir,
                    cache=cache,
                    pointer=pointer,
                    visited=visited | {vkey},
                )
    ns = schema.get(REFERENCE_NAMESPACE_ANNOTATION)
    if isinstance(ns, str):
        yield ns, data, pointer
    props = schema.get("properties")
    if isinstance(props, dict) and isinstance(data, dict):
        for key, sub in props.items():
            if isinstance(key, str) and key in data:
                yield from _collect_reference_checks(
                    sub,
                    data[key],
                    companion_path=companion_path,
                    schemas_dir=schemas_dir,
                    cache=cache,
                    pointer=f"{pointer}/{key}",
                    visited=visited,
                )
    items = schema.get("items")
    if isinstance(items, dict) and isinstance(data, list):
        for idx, element in enumerate(data):
            yield from _collect_reference_checks(
                items,
                element,
                companion_path=companion_path,
                schemas_dir=schemas_dir,
                cache=cache,
                pointer=f"{pointer}/{idx}",
                visited=visited,
            )
    for keyword in ("allOf", "anyOf", "oneOf"):
        branch = schema.get(keyword)
        if isinstance(branch, list):
            for sub in branch:
                yield from _collect_reference_checks(
                    sub,
                    data,
                    companion_path=companion_path,
                    schemas_dir=schemas_dir,
                    cache=cache,
                    pointer=pointer,
                    visited=visited,
                )


def _build_namespace_pools(
    instances: list[tuple[ResolvedBinding, Any]],
    target_root: Path,
    cache: dict[Path, Any],
) -> tuple[dict[tuple[str, str], _NsPool], list[DataValidationIssue]]:
    """Build the per-(capability, namespace) id pool across all in-scope instances.

    A file bound to `<cap>:<ns>` is an *instance* of namespace `ns`; its
    ids (read via `ns`'s companion `x-pkit-id-collection`, applied to the
    instance's data) join the pool for `(cap, ns)`. Returns the pools plus
    any duplicate-id findings (the same id in two in-scope instances of one
    namespace makes the pool ambiguous — a hard error per COR-029).
    """
    # key -> id -> list of files defining it (for duplicate detection).
    raw: dict[tuple[str, str], dict[str, list[Path]]] = {}
    errors_by_key: dict[tuple[str, str], str] = {}
    for binding, data in instances:
        key = (binding.capability, binding.schema_name)
        if key in errors_by_key:
            continue
        companion = _companion_json(binding.companion, cache)
        if companion is None:
            errors_by_key[key] = (
                f"companion {binding.companion.name!r} is unreadable or not valid JSON"
            )
            continue
        pointer = companion.get(_ID_COLLECTION_ANNOTATION)
        if not isinstance(pointer, str):
            errors_by_key[key] = (
                f"namespace {binding.schema_name!r} declares no "
                f"{_ID_COLLECTION_ANNOTATION!r} in its companion; references to it "
                f"cannot resolve"
            )
            continue
        try:
            collection = _resolve_json_pointer(_stringify_dates(data), pointer)
        except (KeyError, ValueError):
            collection = None
        ids = _collect_ids(collection) if collection is not None else []
        bucket = raw.setdefault(key, {})
        for id_value in ids or []:
            bucket.setdefault(id_value, []).append(binding.data_path)

    pools: dict[tuple[str, str], _NsPool] = {}
    dup_issues: list[DataValidationIssue] = []
    for key, bucket in raw.items():
        pools[key] = _NsPool(ids=frozenset(bucket))
        cap, ns = key
        for id_value, files in bucket.items():
            if len(files) > 1:
                rels = ", ".join(sorted(_rel(f, target_root) for f in files))
                dup_issues.append(
                    DataValidationIssue(
                        location=f"{cap}:{ns}",
                        message=(
                            f"duplicate id {id_value!r} for namespace {ns!r}: defined "
                            f"in {rels}. The id pool in this scope is ambiguous "
                            f"(per COR-029)."
                        ),
                        severity="error",
                    )
                )
    for key, message in errors_by_key.items():
        pools[key] = _NsPool(error=message)
    return pools, dup_issues


def _check_reference_value(
    ns_annot: str,
    value: Any,
    pointer: str,
    binding: ResolvedBinding,
    pools: dict[tuple[str, str], _NsPool],
    target_root: Path,
) -> list[DataValidationIssue]:
    """Validate the token(s) at one reference-annotated data position."""
    rel = _rel(binding.data_path, target_root)
    pairs: list[tuple[str, str]] = []
    if isinstance(value, str):
        pairs.append((value, pointer))
    elif isinstance(value, list):
        for idx, element in enumerate(value):
            if isinstance(element, str):
                pairs.append((element, f"{pointer}/{idx}"))
    else:
        # Missing / null / wrong-typed — the shape pass owns that finding.
        return []

    key = (binding.capability, ns_annot)
    issues: list[DataValidationIssue] = []
    for token, ptr in pairs:
        loc = f"{rel}{ptr}"
        match = _TOKEN_PATTERN.match(token)
        if match is None:
            issues.append(
                DataValidationIssue(
                    location=loc,
                    message=(
                        f"value {token!r} at a reference position is not a "
                        f"[namespace:id] token (the field declares "
                        f"{REFERENCE_NAMESPACE_ANNOTATION}: {ns_annot!r})."
                    ),
                    severity="error",
                )
            )
            continue
        token_ns, token_id = match.group(1), match.group(2)
        if token_ns != ns_annot:
            issues.append(
                DataValidationIssue(
                    location=loc,
                    message=(
                        f"reference {token!r} is in namespace {token_ns!r} but this "
                        f"position declares {ns_annot!r}."
                    ),
                    severity="error",
                )
            )
            continue
        pool = pools.get(key)
        if pool is None:
            issues.append(
                DataValidationIssue(
                    location=loc,
                    message=(
                        f"no file bound to namespace {ns_annot!r} found in the "
                        f"validation scope; cannot resolve {token!r}. An in-progress "
                        f"reference to a not-yet-created instance is normal "
                        f"(per COR-029)."
                    ),
                    severity="warning",
                )
            )
            continue
        if pool.error is not None:
            issues.append(
                DataValidationIssue(
                    location=loc,
                    message=f"cannot resolve {token!r}: {pool.error}.",
                    severity="error",
                )
            )
            continue
        if token_id not in pool.ids:
            cap, _ = key
            issues.append(
                DataValidationIssue(
                    location=loc,
                    message=(
                        f"unresolved reference {token!r}: id {token_id!r} not found "
                        f"among files bound to {cap}:{ns_annot} in the validation scope."
                    ),
                    severity="error",
                )
            )
    return issues


def _resolve_references_in_scope(
    instances: list[tuple[ResolvedBinding, Any]],
    target_root: Path,
) -> list[DataValidationIssue]:
    """Run the scope-subtree cross-file reference pass over all bound instances."""
    cache: dict[Path, Any] = {}
    pools, dup_issues = _build_namespace_pools(instances, target_root, cache)
    issues: list[DataValidationIssue] = list(dup_issues)
    for binding, data in instances:
        companion = _companion_json(binding.companion, cache)
        if companion is None:
            continue
        for ns_annot, value, pointer in _collect_reference_checks(
            companion,
            _stringify_dates(data),
            companion_path=binding.companion,
            schemas_dir=binding.companion.parent,
            cache=cache,
            pointer="",
            visited=frozenset(),
        ):
            issues.extend(
                _check_reference_value(
                    ns_annot, value, pointer, binding, pools, target_root
                )
            )
    return issues


# --- orchestration ------------------------------------------------------


def validate_path(
    path: Path, target_root: Path, *, resolve_references: bool = True
) -> DataValidationReport:
    """Validate every adopter data file at `path` (file or directory).

    Runs the shape pass per file, then — unless `resolve_references` is
    False (the CLI's `--shape-only`) — the scope-subtree cross-file
    reference pass over every file whose binding resolved. The validation
    scope is exactly `path`: the id pool a reference resolves against is the
    union of in-scope files bound to its namespace (per COR-029).
    """
    files = discover_data_files(path)
    if not files:
        return DataValidationReport(files_checked=0, issues=())
    # Load capability bindings once for the whole run.
    cap_bindings = load_all_capability_bindings(target_root)
    all_issues: list[DataValidationIssue] = []
    instances: list[tuple[ResolvedBinding, Any]] = []
    for data_path in files:
        all_issues.extend(
            validate_data_file(
                data_path, target_root, capability_bindings=cap_bindings
            )
        )
        if resolve_references:
            binding = resolve_binding(
                data_path, target_root, capability_bindings=cap_bindings
            )
            if isinstance(binding, ResolvedBinding):
                try:
                    data = _yaml.load(data_path.read_text(encoding="utf-8"))
                except (YAMLError, OSError):
                    data = None
                if data is not None:
                    instances.append((binding, data))
    if resolve_references and instances:
        all_issues.extend(_resolve_references_in_scope(instances, target_root))
    return DataValidationReport(files_checked=len(files), issues=tuple(all_issues))


def print_report(report: DataValidationReport) -> None:
    """Render a report to stdout in the style of `pkit schemas validate`.

    Errors and warnings are tagged. A run with only warnings (e.g. an
    in-progress reference to a not-yet-created instance, per COR-029) still
    reports them but does not fail the command — see `has_errors`.
    """
    if report.is_clean:
        if report.files_checked == 0:
            click.echo("  No adopter data files found to validate.")
        else:
            click.echo(
                f"  Validated {report.files_checked} data file(s). All checks passed."
            )
        return

    errors = report.errors
    warnings = report.warnings
    click.echo(
        f"  {len(errors)} error(s), {len(warnings)} warning(s) across "
        f"{report.files_checked} data file(s):"
    )
    for issue in report.issues:
        click.echo(f"    [{issue.severity}] {issue.location}")
        click.echo(f"      → {issue.message}")
