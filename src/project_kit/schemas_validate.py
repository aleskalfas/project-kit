"""Schema validation — YAML schemas against their JSON Schema companions + cross-file reference resolution.

Per the conventions in `.pkit/schemas/` + COR-018 / COR-019: every
capability YAML schema ships a companion JSON Schema at the side-by-side
path `<name>.schema.json`; cross-schema data references use the typed
token form `[<namespace>:<id>]`. This module discovers schema pairs,
validates each YAML against its companion via the `jsonschema` library
(shape pass), and resolves every typed-token reference against the
target namespace's id collection (resolver pass).

Two passes run by default:

- **Shape** — does the YAML satisfy the JSON Schema's structural rules
  (required fields, types, patterns, enum constraints)? Implemented by
  jsonschema's Draft202012Validator.

- **Reference resolution** — for every value or key that matches the
  token pattern `^\\[<namespace>:<id>\\]$`, locate `<namespace>.schema.json`
  in the same directory, read its `x-pkit-id-collection` annotation
  (a JSON Pointer to the id-bearing collection in `<namespace>.yaml`),
  and confirm `<id>` is a key of that collection (or — for list-of-
  objects collections — the `.id` field of some entry). Sibling-file
  scope: cross-directory resolution is not supported in v1.

Both passes contribute issues to the report. The resolver pass is
controlled by the `resolve` parameter (default True) so an author
mid-refactor can run shape-only via `pkit schemas validate --shape-only`.

Discovery: walks `<target_root>/.pkit/capabilities/*/schemas/` for YAML
files; for each, looks for a sibling `<name>.schema.json`. A YAML
without a companion surfaces as an issue (per COR-018 the companion is
required). The validator can also operate on a specific path passed in
explicitly — useful for adopters running the validator against
non-capability data files that follow the same conventions.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import click
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from project_kit import cli_render
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


_yaml = YAML(typ="safe")

# Matches a kebab-case namespace:id token wrapped in square brackets, per COR-019.
# Namespace and id are each kebab-case starting with a lowercase letter.
_TOKEN_PATTERN = re.compile(r"^\[([a-z][a-z0-9-]*):([a-z][a-z0-9-]*)\]$")

# Matches the leading `'<token>' does not match ` portion of a jsonschema
# pattern-mismatch error message *whose failing instance is a typed token*.
# Used to suppress these messages when the resolver pass has already
# explained the namespace mismatch at the same data location.
_SHAPE_TOKEN_NOMATCH_PATTERN = re.compile(
    r"^'\[[a-z][a-z0-9-]*:[a-z][a-z0-9-]*\]' does not match "
)

# JSON Schema annotation declaring where a schema's id collection lives.
# The value is a JSON Pointer (RFC 6901) into the YAML data. e.g.,
# `"x-pkit-id-collection": "/types"` says ids are the keys (or .id fields)
# of the top-level `types` mapping.
_ID_COLLECTION_ANNOTATION = "x-pkit-id-collection"

# JSON Schema annotation declaring that a mapping's keys reference ids in
# another namespace, without expressing the reference in token form at
# each key. Lives on a schema property whose value is a `type: object`
# (or `patternProperties`-shaped mapping). The resolver walks each key
# and confirms it exists in the named namespace.
#
# Example use in body-format.schema.json:
#   "issues": {
#     "type": "object",
#     "x-pkit-keys-from-namespace": "issue-types",
#     "patternProperties": {"^[a-z][a-z0-9-]*$": {...}}
#   }
#
# This lets authoring stay clean at the definition site (`issues.epic: {...}`
# instead of `issues."[issue-types:epic]": {...}`) without losing cross-
# file validation. Per COR-019's third refinement on mapping keys.
_KEYS_FROM_NAMESPACE_ANNOTATION = "x-pkit-keys-from-namespace"


@dataclass(frozen=True)
class SchemaPair:
    """A YAML schema paired with its JSON Schema companion."""

    yaml_path: Path
    companion_path: Path  # may not exist on disk; check is_file()


@dataclass(frozen=True)
class ValidationIssue:
    """One finding from the validator — location + diagnosis."""

    location: str  # path-relative-to-target or "<path>:<json-pointer>"
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of a validation run."""

    pairs_checked: int = 0
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def is_clean(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class _NamespaceTarget:
    """Resolved target namespace: where ids live in the YAML + the set of valid ids."""

    namespace: str
    id_collection_pointer: str
    valid_ids: frozenset[str]


@dataclass(frozen=True)
class SchemaSummary:
    """High-level info about one schema for `pkit schemas list` output."""

    capability: str
    name: str  # the YAML stem; also the namespace name when the schema owns one
    yaml_path: Path
    companion_path: Path
    has_companion: bool
    is_namespace_owner: bool  # True iff the companion has x-pkit-id-collection
    id_collection_pointer: str | None
    entry_ids: tuple[str, ...]  # populated only when is_namespace_owner
    load_error: str | None  # non-None if discovery hit a problem


@dataclass(frozen=True)
class NamespaceDetail:
    """Detailed info about a namespace for `pkit schemas show` output."""

    namespace: str
    capability: str
    yaml_path: Path
    companion_path: Path
    id_collection_pointer: str
    entries: tuple[tuple[str, Any], ...]  # ordered (id, entry_data) tuples


@dataclass(frozen=True)
class TokenResolution:
    """Result of resolving a typed token to its target entry."""

    token: str
    namespace: str
    id: str
    yaml_path: Path
    companion_path: Path
    entry: Any  # the data at the target id (mapping value or list item)


# Cache entry for namespace lookups: either a successful resolution or an
# error message describing why the namespace couldn't be loaded. Cached per
# (schemas_dir, namespace) so multiple references hit one file system pass.
_NamespaceCacheEntry = _NamespaceTarget | str
_NamespaceCache = dict[tuple[Path, str], _NamespaceCacheEntry]


def discover_schema_pairs(target_root: Path) -> list[SchemaPair]:
    """Discover all (YAML, companion) pairs under installed capabilities.

    Walks `<target_root>/.pkit/capabilities/*/schemas/*.yaml`. For each
    YAML, derives the expected companion path
    `<name>.schema.json` in the same directory. Returns the pair
    regardless of whether the companion exists; missing-companion is a
    validation issue, not a discovery failure.
    """
    capabilities_dir = target_root / ".pkit" / "capabilities"
    pairs: list[SchemaPair] = []
    if not capabilities_dir.is_dir():
        return pairs
    for cap_dir in sorted(capabilities_dir.iterdir()):
        schemas_dir = cap_dir / "schemas"
        if not schemas_dir.is_dir():
            continue
        for yaml_path in sorted(schemas_dir.glob("*.yaml")):
            companion = yaml_path.with_suffix(".schema.json")
            pairs.append(SchemaPair(yaml_path=yaml_path, companion_path=companion))
    return pairs


# Matches a `# yaml-language-server: $schema=<path>` directive comment (the
# IDE-side binding, per COR-023) anywhere in a YAML file's leading comment
# block. `<path>` is captured so we can tell a self-companion pointer
# (`<name>.schema.json`, which still requires the companion) from an external
# one (a shared/foreign schema, which means the YAML is an instance).
_LANGUAGE_SERVER_SCHEMA_PATTERN = re.compile(
    r"^\s*#\s*yaml-language-server:\s*\$schema\s*=\s*(?P<target>\S+)"
)

# How many leading lines of a YAML we scan for the language-server directive
# and a top-level `$schema:` key. The directive is a header comment by
# convention; a top-level key sits in the first data lines. Bounding the scan
# keeps the non-schema check cheap on large instance files.
_INSTANCE_MARKER_SCAN_LINES = 40


def _companion_pointer_is_external(target: str, own_companion_name: str) -> bool:
    """True when a `$schema` pointer names something other than the YAML's own companion.

    A pointer at the side-by-side `<name>.schema.json` is the ordinary schema
    pair — the companion is still required. A pointer at any *other* schema
    (a shared `_defs/process.schema.json`, a capability's describing schema)
    marks the YAML as an *instance* validated against that external schema, so
    it needs no companion of its own.
    """
    # Compare on the basename so relative/absolute prefixes don't matter.
    return Path(target).name != own_companion_name


def _yaml_declares_external_schema(yaml_path: Path) -> bool:
    """True when the YAML declares a `$schema` pointing at an external/shared schema.

    Two signals, either sufficient (per the `.pkit/schemas/` companion-scope
    convention + COR-023's IDE-directive form):

    - a `# yaml-language-server: $schema=<path>` directive comment, or
    - a top-level `$schema:` key,

    whose target is a schema *other than* this YAML's own
    `<name>.schema.json`. Such a YAML is an instance validated against the
    named schema, not a schema definition — so it requires no companion.

    Read failures are treated as "no external declaration": a genuinely broken
    file is left to surface as a normal validation issue rather than being
    silently excluded from the schema surface.
    """
    own_companion_name = yaml_path.with_suffix(".schema.json").name
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for line in text.splitlines()[:_INSTANCE_MARKER_SCAN_LINES]:
        m = _LANGUAGE_SERVER_SCHEMA_PATTERN.match(line)
        if m and _companion_pointer_is_external(m.group("target"), own_companion_name):
            return True
        # Top-level `$schema:` key — column 0, no leading indent.
        stripped = line.rstrip()
        if stripped.startswith("$schema:") and not line[:1].isspace():
            target = stripped[len("$schema:"):].strip().strip("'\"")
            if target and _companion_pointer_is_external(target, own_companion_name):
                return True
    return False


def _is_schema_definition(yaml_path: Path) -> bool:
    """True when a YAML under a schemas tree is an actual schema definition.

    A YAML requires a companion JSON Schema (COR-018) only if it *is* a schema
    definition. Non-schema YAML — fixtures and instances that live alongside
    real schemas — is excluded via principled, project-neutral signals so the
    companion requirement doesn't fire on files that categorically can't have a
    companion:

    - **`examples/` material.** YAML under any `examples/` directory, or named
      `*-example.yaml`, is an instance/fixture — never a schema.
    - **Instances of an external schema.** YAML declaring a `$schema` pointer
      (language-server directive or top-level key) at a schema other than its
      own companion is validated against that shared/external schema, so it
      owns no companion of its own (e.g. process-definition YAMLs validated
      against a shared `_defs/process.schema.json`).

    Everything else is treated as a schema definition and must ship a
    companion — preserving the COR-018 check on genuine schema YAML.
    """
    if any(part == "examples" for part in yaml_path.parts):
        return False
    if yaml_path.stem.endswith("-example"):
        return False
    return not _yaml_declares_external_schema(yaml_path)


def discover_schema_pairs_at(path: Path) -> list[SchemaPair]:
    """Discover schema pairs for a specific path (a file or a directory).

    If `path` is a YAML file, returns one pair (the path is taken to be a
    schema the caller means to validate). If it's a directory, walks it for
    schema-definition YAML — excluding non-schema YAML (fixtures under
    `examples/`, instances of an external `$schema`) via `_is_schema_definition`
    so the COR-018 companion requirement fires only on actual schemas. This
    keeps the directory walk aligned with `discover_schema_pairs`' convention
    that a schema is a direct `schemas/<name>.yaml` with a side-by-side
    companion; subdirectories (`examples/`, `_defs/`) hold non-schema material.
    Companion path is derived the same way in both branches.
    """
    pairs: list[SchemaPair] = []
    if path.is_file() and path.suffix == ".yaml":
        pairs.append(
            SchemaPair(yaml_path=path, companion_path=path.with_suffix(".schema.json"))
        )
    elif path.is_dir():
        for yaml_path in sorted(path.rglob("*.yaml")):
            # Skip companion side-cars and other generated files if any sneak in.
            if yaml_path.name.endswith(".schema.json"):
                continue
            if not _is_schema_definition(yaml_path):
                continue
            companion = yaml_path.with_suffix(".schema.json")
            pairs.append(SchemaPair(yaml_path=yaml_path, companion_path=companion))
    return pairs


def validate_pair(
    pair: SchemaPair,
    target_root: Path | None = None,
    *,
    resolve: bool = True,
    namespace_cache: _NamespaceCache | None = None,
    shared_registry: Registry | None = None,
) -> list[ValidationIssue]:
    """Validate one YAML against its companion + (by default) resolve token references.

    Two passes:
    - Shape — does the YAML satisfy the JSON Schema?
    - References (when `resolve=True`) — does every `[<namespace>:<id>]`
      token in the YAML resolve to a real id in the named namespace?

    `namespace_cache` is shared across pairs in a multi-pair run so each
    namespace is loaded once.

    `shared_registry`, if provided, is used directly (the caller has
    already loaded all sibling companions + the kit-wide _defs and
    reported any load failures). If None, this function builds a local
    registry — convenient for single-pair invocations.

    Returns the findings (empty = clean).
    """
    issues: list[ValidationIssue] = []
    yaml_rel = _rel(pair.yaml_path, target_root)
    companion_rel = _rel(pair.companion_path, target_root)

    # 1. Companion must exist.
    if not pair.companion_path.is_file():
        issues.append(
            ValidationIssue(
                location=yaml_rel,
                message=f"missing companion JSON Schema at {companion_rel} "
                f"(required per COR-018; every YAML schema ships a companion).",
            )
        )
        return issues

    # 2. Companion must parse + be a valid JSON Schema itself.
    try:
        schema = json.loads(pair.companion_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(
            ValidationIssue(
                location=companion_rel,
                message=f"companion is not valid JSON: {exc.msg} at line {exc.lineno} col {exc.colno}.",
            )
        )
        return issues
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        issues.append(
            ValidationIssue(
                location=companion_rel,
                message=f"companion is not a valid Draft 2020-12 JSON Schema: {exc.message}",
            )
        )
        return issues

    # 3. YAML must parse.
    try:
        data = _yaml.load(pair.yaml_path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        issues.append(
            ValidationIssue(
                location=yaml_rel,
                message=f"YAML parse error: {exc}",
            )
        )
        return issues

    # 4. Shape pass — validate YAML against the JSON Schema. Build a
    # Registry so cross-file `$ref`s (e.g., to `_defs/refs.schema.json`
    # or a sibling companion that owns a namespace's narrowed pattern)
    # resolve at validation time per COR-019's single-source-of-truth
    # convention for shared $defs.
    data = _stringify_dates(data)
    if shared_registry is None:
        registry, registry_issues = _build_ref_registry(pair, target_root)
        issues.extend(registry_issues)
    else:
        registry = shared_registry
    validator = Draft202012Validator(schema, registry=registry)
    # `iter_errors` can raise `Unresolvable` when a `$ref` points at a
    # schema that's missing from the registry — typically because the
    # target file is missing or malformed. Catch it cleanly rather than
    # crashing with a stack trace.
    try:
        shape_errors = list(validator.iter_errors(data))
    except Unresolvable as exc:
        issues.append(
            ValidationIssue(
                location=yaml_rel,
                message=f"cross-file $ref could not resolve: {exc.ref!r}. "
                f"The target schema may be missing, malformed, or lack the "
                f"referenced $defs entry. See sibling-companion issues above.",
            )
        )
        shape_errors = []
    for error in sorted(shape_errors, key=lambda e: list(e.absolute_path)):
        pointer = "/" + "/".join(str(p) for p in error.absolute_path) if error.absolute_path else ""
        issues.append(
            ValidationIssue(
                location=f"{yaml_rel}{pointer}",
                message=error.message,
            )
        )

    # 5. Reference-resolution pass — walk every typed-token reference in
    # the YAML (value-position references), plus every mapping field
    # carrying an `x-pkit-keys-from-namespace` annotation (key-position
    # references). Both verify against the named namespace's id
    # collection.
    if resolve:
        if namespace_cache is None:
            namespace_cache = {}
        issues.extend(
            _resolve_references(pair, data, namespace_cache, yaml_rel)
        )
        issues.extend(
            _resolve_key_references(pair, schema, data, namespace_cache, yaml_rel)
        )
    # 6. Suppress shape pattern-mismatch issues where the resolver has
    # already explained the same data position with a more informative
    # message (e.g., a wrong-namespace token fires both checks; only the
    # resolver's "unresolved reference" message tells the user what's
    # actually wrong).
    return _dedup_pattern_when_resolver_covers(issues)


def validate_all(target_root: Path, *, resolve: bool = True) -> ValidationReport:
    """Discover + validate every capability schema pair under target_root.

    Per COR-023 (superseding COR-022): there is no separate
    `bindings.yaml` file to validate — adopter-data binding patterns
    live in each schema YAML's optional `binds_to:` field and are
    validated implicitly by the schema's existing envelope. Schema
    pair validation alone is the surface here.

    Also runs the capability-fragment grant-token lint (ADR-021): for every
    installed capability's `permissions/grants.yaml`, each grant's privilege
    token must resolve to a privilege in the MERGED catalog, or the deny
    silently does not bind (the bare-vs-scoped fail-open hazard). This pass is
    scoped to the full project (it needs the manifest + merged catalog), so it
    runs only in the no-PATH `validate_all` gate, not in `validate_path`.
    """
    pairs = discover_schema_pairs(target_root)
    report = _run_validation(pairs, target_root, resolve=resolve)
    fragment_issues = _lint_fragment_grant_tokens(target_root)
    if not fragment_issues:
        return report
    return ValidationReport(
        pairs_checked=report.pairs_checked,
        issues=report.issues + tuple(fragment_issues),
    )


def _lint_fragment_grant_tokens(target_root: Path) -> list[ValidationIssue]:
    """Adapt the permissions module's fragment-grant-token lint to ValidationIssues.

    The lint itself (`permissions.lint_capability_fragment_grants`) lives with
    the permission code because it reuses the decision core's merge + token
    normaliser to agree with the runtime exactly (ADR-021); this wrapper maps
    its findings into the validation report so `pkit schemas validate` is the
    single gate the kit runs on capability-side spec.
    """
    from project_kit import permissions as perm

    issues: list[ValidationIssue] = []
    for finding in perm.lint_capability_fragment_grants(target_root):
        issues.append(
            ValidationIssue(
                location=_rel(finding.grants_path, target_root),
                message=f"grant token {finding.token!r}: {finding.fix_hint}",
            )
        )
    return issues


def validate_path(
    path: Path, target_root: Path | None = None, *, resolve: bool = True
) -> ValidationReport:
    """Validate the YAML schemas at a specific path (file or directory)."""
    pairs = discover_schema_pairs_at(path)
    return _run_validation(pairs, target_root, resolve=resolve)


def print_report(report: ValidationReport) -> None:
    """Render the report to stdout (and stderr for issues), in the style of `pkit refs validate`."""
    if report.is_clean:
        if report.pairs_checked == 0:
            click.echo("  No schemas found to validate.")
        else:
            click.echo("  " + cli_render.style("strong", f"Validated {report.pairs_checked} schema(s). All checks passed."))
        return

    click.echo("  " + cli_render.style("strong", f"{len(report.issues)} issue(s) found across {report.pairs_checked} schema(s):"))
    for issue in report.issues:
        click.echo(f"    {issue.location}")
        click.echo(f"      → {issue.message}")


def _run_validation(
    pairs: list[SchemaPair], target_root: Path | None, *, resolve: bool = True
) -> ValidationReport:
    # Build the registry once for the whole run. Schema-load failures
    # become issues against their own paths, reported once each rather
    # than once per consumer pair.
    registry, registry_issues = _build_shared_registry(pairs, target_root)
    all_issues: list[ValidationIssue] = list(registry_issues)
    # Cache namespace targets across pairs so loading `issue-types.yaml`
    # once serves every schema that references it.
    namespace_cache: _NamespaceCache = {}
    for pair in pairs:
        all_issues.extend(
            validate_pair(
                pair,
                target_root=target_root,
                resolve=resolve,
                namespace_cache=namespace_cache,
                shared_registry=registry,
            )
        )
    return ValidationReport(pairs_checked=len(pairs), issues=tuple(all_issues))


def _rel(path: Path, target_root: Path | None) -> str:
    """Render a path relative to target_root when possible; otherwise absolute."""
    if target_root is None:
        return str(path)
    try:
        return str(path.relative_to(target_root))
    except ValueError:
        return str(path)


def _stringify_dates(obj: Any) -> Any:
    """Coerce date / datetime values to ISO strings so jsonschema's `format: date` matches.

    YAML's `2026-05-20` parses to a `datetime.date` object; jsonschema's
    `format: date` expects a string. Convert recursively before
    validation. Other types pass through unchanged.
    """
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(x) for x in obj]
    if isinstance(obj, _dt.date):
        return obj.isoformat()
    return obj


# --- issue post-processing ----------------------------------------------


def _dedup_pattern_when_resolver_covers(
    issues: list[ValidationIssue],
) -> list[ValidationIssue]:
    """Drop shape pattern-mismatch issues already explained by the resolver.

    When a schema's field uses a narrowed token pattern (e.g.,
    `^\\[issue-types:[a-z][a-z0-9-]*\\]$`) and the YAML has a typed
    token from a different namespace, both passes fire at the same
    data position:

    - Shape pass: `'[unknownns:task]' does not match '^\\[issue-types:...$'`
    - Resolver pass: `unresolved reference '[unknownns:task]': sibling
      companion 'unknownns.schema.json' not found ...`

    Both are correct, but the resolver one is strictly more informative
    — it names the namespace conflict and tells the user where the
    missing sibling should live. The shape one just says "doesn't match
    pattern." Drop it.

    Only suppresses shape errors when:
    1. A resolver `unresolved reference` issue covers the same location.
    2. The shape error's failing instance is itself a typed token.

    Non-token pattern errors (e.g., a malformed kebab-case id, a wrong-
    shape free-form string) survive untouched.
    """
    resolver_covered = {
        issue.location
        for issue in issues
        if issue.message.startswith("unresolved reference")
    }
    if not resolver_covered:
        return issues
    return [
        issue
        for issue in issues
        if not (
            issue.location in resolver_covered
            and _SHAPE_TOKEN_NOMATCH_PATTERN.match(issue.message)
        )
    ]


# --- cross-file $ref resolution (shape pass) ---------------------------


def _build_ref_registry(
    pair: SchemaPair, target_root: Path | None
) -> tuple[Registry, list[ValidationIssue]]:
    """Build a Registry covering every JSON Schema relevant to this pair.

    A companion's `$ref` may point at:
    - Its own `$defs` (handled natively — same-file resolution).
    - A sibling companion in the same dir (e.g., a consumer of the
      `issue-types` namespace references `issue-types.schema.json#/$defs/
      issue_type_ref` — the namespace owner publishes its narrowed
      reference pattern in its own `$defs`).
    - The kit-wide shared library at `<target_root>/.pkit/schemas/_defs/
      refs.schema.json` — generic patterns (`reference_token`, `source`)
      that recur across capabilities.

    Each schema in scope registers under its `$id` so relative URIs
    (`issue-types.schema.json#/$defs/issue_type_ref`) resolve cleanly.

    Returns (Registry, issues). Schemas that fail to load surface as
    issues against their own path — the caller decides whether to
    report them (typically once per scan).
    """
    return _build_registry_for_paths(
        _collect_registry_paths(pair, target_root),
        target_root,
        already_reported=set(),
    )


def _build_shared_registry(
    pairs: list[SchemaPair], target_root: Path | None
) -> tuple[Registry, list[ValidationIssue]]:
    """Build one registry covering every schema in scope for `pairs`.

    Used at the top of a multi-pair run so schema-load failures are
    reported once each rather than once per consumer pair.
    """
    paths: list[Path] = []
    seen: set[Path] = set()
    for pair in pairs:
        for p in _collect_registry_paths(pair, target_root):
            if p not in seen:
                seen.add(p)
                paths.append(p)
    return _build_registry_for_paths(paths, target_root, already_reported=set())


def _collect_registry_paths(pair: SchemaPair, target_root: Path | None) -> list[Path]:
    """All `.schema.json` files relevant to a pair's `$ref` resolution."""
    paths: list[Path] = []
    schemas_dir = pair.yaml_path.parent
    paths.extend(sorted(schemas_dir.glob("*.schema.json")))
    if target_root is not None:
        defs_dir = target_root / ".pkit" / "schemas" / "_defs"
        if defs_dir.is_dir():
            paths.extend(sorted(defs_dir.glob("*.schema.json")))
    return paths


def _build_registry_for_paths(
    paths: list[Path],
    target_root: Path | None,
    already_reported: set[Path],
) -> tuple[Registry, list[ValidationIssue]]:
    """Load each schema into a Registry; collect issues for any that fail to load."""
    registry = Registry()
    issues: list[ValidationIssue] = []
    for schema_path in paths:
        registry, issue = _try_add_to_registry(registry, schema_path, target_root)
        if issue is not None and schema_path not in already_reported:
            issues.append(issue)
            already_reported.add(schema_path)
    return registry, issues


def _try_add_to_registry(
    registry: Registry, schema_path: Path, target_root: Path | None
) -> tuple[Registry, ValidationIssue | None]:
    """Try to add one schema. Return the (possibly unchanged) registry plus any load issue."""
    schema_rel = _rel(schema_path, target_root)
    try:
        text = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        return registry, ValidationIssue(
            location=schema_rel,
            message=f"could not read sibling companion: {exc}.",
        )
    try:
        schema = json.loads(text)
    except json.JSONDecodeError as exc:
        return registry, ValidationIssue(
            location=schema_rel,
            message=f"sibling companion is not valid JSON (cross-file $ref into it "
            f"will fail): {exc.msg} at line {exc.lineno} col {exc.colno}.",
        )
    uri = schema.get("$id", schema_path.name)
    try:
        resource = Resource.from_contents(schema, default_specification=DRAFT202012)
    except Exception as exc:  # noqa: BLE001 — referencing's surface is broad
        return registry, ValidationIssue(
            location=schema_rel,
            message=f"sibling companion could not be loaded as a Draft 2020-12 "
            f"JSON Schema resource: {exc}",
        )
    return registry.with_resource(uri=uri, resource=resource), None


# --- reference resolution (COR-019) -------------------------------------


def _resolve_references(
    pair: SchemaPair,
    data: Any,
    namespace_cache: _NamespaceCache,
    yaml_rel: str,
) -> list[ValidationIssue]:
    """Walk every typed-token in `data`, emit issues for any that don't resolve."""
    issues: list[ValidationIssue] = []
    schemas_dir = pair.yaml_path.parent
    own_namespace = pair.yaml_path.stem
    for token, namespace, id_value, location_pointer in _walk_tokens(data):
        # Self-namespace reference — should be bare per COR-019. Flag it,
        # because shape validation alone won't catch it (the token regex
        # matches the schema's own namespace just like any other).
        if namespace == own_namespace:
            issues.append(
                ValidationIssue(
                    location=f"{yaml_rel}{location_pointer}",
                    message=f"reference {token!r} targets the same schema; "
                    f"intra-schema references must be bare (per COR-019).",
                )
            )
            continue
        cache_key = (schemas_dir, namespace)
        if cache_key not in namespace_cache:
            namespace_cache[cache_key] = _load_namespace_target(schemas_dir, namespace)
        result = namespace_cache[cache_key]
        if isinstance(result, str):
            issues.append(
                ValidationIssue(
                    location=f"{yaml_rel}{location_pointer}",
                    message=f"unresolved reference {token!r}: {result}",
                )
            )
            continue
        if id_value not in result.valid_ids:
            issues.append(
                ValidationIssue(
                    location=f"{yaml_rel}{location_pointer}",
                    message=f"unresolved reference {token!r}: id {id_value!r} "
                    f"not found in namespace {namespace!r}.",
                )
            )
    return issues


def _walk_tokens(
    data: Any, path: tuple[str, ...] = ()
) -> Iterator[tuple[str, str, str, str]]:
    """Yield (token, namespace, id, location_pointer) for every token-shaped string.

    Walks both keys and values. `location_pointer` is a JSON-Pointer-style
    string (with leading `/`) for value positions, or `/<parent>/(key)<token>`
    for keys, so reports distinguish key-position from value-position
    references.
    """
    if isinstance(data, dict):
        for k, v in data.items():
            key_str = str(k)
            if _TOKEN_PATTERN.match(key_str):
                m = _TOKEN_PATTERN.match(key_str)
                assert m is not None
                pointer = "/" + "/".join(path) + ("/" if path else "") + f"(key){key_str}"
                yield key_str, m.group(1), m.group(2), pointer
            yield from _walk_tokens(v, path + (key_str,))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            yield from _walk_tokens(item, path + (str(idx),))
    elif isinstance(data, str):
        m = _TOKEN_PATTERN.match(data)
        if m:
            pointer = "/" + "/".join(path) if path else ""
            yield data, m.group(1), m.group(2), pointer


def _load_namespace_target(schemas_dir: Path, namespace: str) -> _NamespaceCacheEntry:
    """Load a target namespace's id collection. Returns the resolved target or an error string."""
    companion = schemas_dir / f"{namespace}.schema.json"
    yaml_file = schemas_dir / f"{namespace}.yaml"
    if not companion.is_file():
        return (
            f"sibling companion {companion.name!r} not found "
            f"(expected at {schemas_dir.name}/{companion.name})"
        )
    try:
        schema = json.loads(companion.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return f"sibling companion {companion.name!r} not valid JSON: {exc.msg}"
    pointer = schema.get(_ID_COLLECTION_ANNOTATION)
    if pointer is None:
        return (
            f"sibling companion {companion.name!r} missing {_ID_COLLECTION_ANNOTATION!r} "
            f"annotation (required for cross-file resolution)"
        )
    if not isinstance(pointer, str):
        return (
            f"sibling companion {companion.name!r} has non-string "
            f"{_ID_COLLECTION_ANNOTATION!r}: {pointer!r}"
        )
    if not yaml_file.is_file():
        return f"sibling data file {yaml_file.name!r} not found at {schemas_dir.name}/{yaml_file.name}"
    try:
        yaml_data = _yaml.load(yaml_file.read_text(encoding="utf-8"))
    except YAMLError as exc:
        return f"sibling data file {yaml_file.name!r} unparseable: {exc}"
    yaml_data = _stringify_dates(yaml_data)
    try:
        collection = _resolve_json_pointer(yaml_data, pointer)
    except (KeyError, ValueError) as exc:
        return (
            f"{_ID_COLLECTION_ANNOTATION} pointer {pointer!r} in "
            f"{companion.name!r} did not resolve: {exc}"
        )
    valid_ids = _collect_ids(collection)
    if valid_ids is None:
        return (
            f"{_ID_COLLECTION_ANNOTATION} pointer {pointer!r} in "
            f"{companion.name!r} resolved to {type(collection).__name__}; "
            f"expected mapping or list-of-objects-with-id"
        )
    return _NamespaceTarget(
        namespace=namespace,
        id_collection_pointer=pointer,
        valid_ids=frozenset(valid_ids),
    )


def _collect_ids(collection: Any) -> list[str] | None:
    """Extract the set of ids from a resolved collection.

    Mapping → its keys. List → each item's `id` field. Other → None
    (caller treats as a failure).
    """
    if isinstance(collection, dict):
        return [str(k) for k in collection.keys()]
    if isinstance(collection, list):
        ids: list[str] = []
        for item in collection:
            if isinstance(item, dict) and "id" in item:
                ids.append(str(item["id"]))
        return ids
    return None


def _walk_keys_from_namespace(
    schema: Any, data_pointer: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], str]]:
    """Walk a JSON Schema for `x-pkit-keys-from-namespace` annotations.

    Yields (data_path, namespace) for each annotation found. `data_path`
    is the chain of property names from the schema root to the annotated
    field; the resolver navigates to that path in the YAML data and
    validates each key in the resulting mapping against the named
    namespace.

    Walks through `properties` chains. Other JSON Schema keywords
    (`patternProperties`, `additionalProperties`, `items`, `oneOf`,
    `anyOf`, etc.) are not traversed in v1 — direct property nesting
    covers every case in the kit's current schemas. Extend when needed.
    """
    if not isinstance(schema, dict):
        return
    ns = schema.get(_KEYS_FROM_NAMESPACE_ANNOTATION)
    if isinstance(ns, str):
        yield data_pointer, ns
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for prop_name, prop_schema in properties.items():
            yield from _walk_keys_from_namespace(prop_schema, data_pointer + (prop_name,))


def _resolve_key_references(
    pair: SchemaPair,
    schema: dict,
    data: Any,
    namespace_cache: _NamespaceCache,
    yaml_rel: str,
) -> list[ValidationIssue]:
    """Walk every field tagged with `x-pkit-keys-from-namespace` and validate its keys."""
    issues: list[ValidationIssue] = []
    schemas_dir = pair.yaml_path.parent
    own_namespace = pair.yaml_path.stem
    for data_path, namespace in _walk_keys_from_namespace(schema):
        # Navigate to the data at the annotated path. Missing or wrong-
        # shape data is the shape pass's concern; we skip silently here.
        node: Any = data
        for part in data_path:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        if not isinstance(node, dict):
            continue
        path_str = "/" + "/".join(data_path) if data_path else ""
        if namespace == own_namespace:
            # Annotating a field whose keys reference the schema's own
            # namespace is wrong — the file IS the namespace declaration
            # and shouldn't reference itself via annotation.
            issues.append(
                ValidationIssue(
                    location=f"{yaml_rel}{path_str}",
                    message=f"x-pkit-keys-from-namespace targets the schema's own namespace; "
                    f"remove the annotation (per COR-019).",
                )
            )
            continue
        cache_key = (schemas_dir, namespace)
        if cache_key not in namespace_cache:
            namespace_cache[cache_key] = _load_namespace_target(schemas_dir, namespace)
        result = namespace_cache[cache_key]
        if isinstance(result, str):
            issues.append(
                ValidationIssue(
                    location=f"{yaml_rel}{path_str}",
                    message=f"x-pkit-keys-from-namespace {namespace!r}: {result}",
                )
            )
            continue
        for key in node.keys():
            key_str = str(key)
            if key_str not in result.valid_ids:
                issues.append(
                    ValidationIssue(
                        location=f"{yaml_rel}{path_str}/{key_str}",
                        message=f"key {key_str!r} not found in namespace {namespace!r} "
                        f"(declared via x-pkit-keys-from-namespace).",
                    )
                )
    return issues


def _resolve_json_pointer(data: Any, pointer: str) -> Any:
    """Resolve a JSON Pointer (RFC 6901) against a parsed YAML/JSON document.

    Raises KeyError if any step fails, ValueError if the pointer is malformed.
    """
    if pointer == "":
        return data
    if not pointer.startswith("/"):
        raise ValueError(f"JSON Pointer must start with '/': {pointer!r}")
    parts = pointer[1:].split("/")
    # RFC 6901 escapes: `~1` -> `/`, `~0` -> `~`.
    parts = [p.replace("~1", "/").replace("~0", "~") for p in parts]
    current = data
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(f"step {part!r} not found in mapping")
            current = current[part]
        elif isinstance(current, list):
            try:
                idx = int(part)
            except ValueError as exc:
                raise KeyError(
                    f"step {part!r} is not an integer index for list"
                ) from exc
            if idx < 0 or idx >= len(current):
                raise KeyError(f"step {part!r} out of range for list of length {len(current)}")
            current = current[idx]
        else:
            raise KeyError(f"cannot traverse {type(current).__name__} at step {part!r}")
    return current


# --- discovery + summary (for `pkit schemas list / show / resolve`) ----


def summarize_schemas(target_root: Path) -> list[SchemaSummary]:
    """Walk installed capabilities and produce a summary of every schema.

    For each `*.yaml` under `<target_root>/.pkit/capabilities/*/schemas/`,
    derives whether the schema owns a namespace (its companion declares
    `x-pkit-id-collection`) and, if so, the set of ids defined in its
    collection. Schemas with load issues surface the error in
    `load_error` instead of crashing the walk.
    """
    summaries: list[SchemaSummary] = []
    capabilities_dir = target_root / ".pkit" / "capabilities"
    if not capabilities_dir.is_dir():
        return summaries
    for cap_dir in sorted(capabilities_dir.iterdir()):
        schemas_dir = cap_dir / "schemas"
        if not schemas_dir.is_dir():
            continue
        for yaml_path in sorted(schemas_dir.glob("*.yaml")):
            summaries.append(_summarize_one(cap_dir.name, yaml_path))
    return summaries


def _summarize_one(capability: str, yaml_path: Path) -> SchemaSummary:
    """Build a `SchemaSummary` for one YAML schema."""
    companion = yaml_path.with_suffix(".schema.json")
    name = yaml_path.stem
    if not companion.is_file():
        return SchemaSummary(
            capability=capability,
            name=name,
            yaml_path=yaml_path,
            companion_path=companion,
            has_companion=False,
            is_namespace_owner=False,
            id_collection_pointer=None,
            entry_ids=(),
            load_error="companion JSON Schema missing",
        )
    try:
        schema = json.loads(companion.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return SchemaSummary(
            capability=capability,
            name=name,
            yaml_path=yaml_path,
            companion_path=companion,
            has_companion=True,
            is_namespace_owner=False,
            id_collection_pointer=None,
            entry_ids=(),
            load_error=f"companion not valid JSON: {exc.msg}",
        )
    pointer = schema.get(_ID_COLLECTION_ANNOTATION)
    if not isinstance(pointer, str):
        return SchemaSummary(
            capability=capability,
            name=name,
            yaml_path=yaml_path,
            companion_path=companion,
            has_companion=True,
            is_namespace_owner=False,
            id_collection_pointer=None,
            entry_ids=(),
            load_error=None,
        )
    try:
        data = _yaml.load(yaml_path.read_text(encoding="utf-8"))
    except YAMLError as exc:
        return SchemaSummary(
            capability=capability,
            name=name,
            yaml_path=yaml_path,
            companion_path=companion,
            has_companion=True,
            is_namespace_owner=True,
            id_collection_pointer=pointer,
            entry_ids=(),
            load_error=f"YAML parse error: {exc}",
        )
    data = _stringify_dates(data)
    try:
        collection = _resolve_json_pointer(data, pointer)
    except (KeyError, ValueError) as exc:
        return SchemaSummary(
            capability=capability,
            name=name,
            yaml_path=yaml_path,
            companion_path=companion,
            has_companion=True,
            is_namespace_owner=True,
            id_collection_pointer=pointer,
            entry_ids=(),
            load_error=f"x-pkit-id-collection {pointer!r} did not resolve: {exc}",
        )
    ids = _collect_ids(collection) or []
    return SchemaSummary(
        capability=capability,
        name=name,
        yaml_path=yaml_path,
        companion_path=companion,
        has_companion=True,
        is_namespace_owner=True,
        id_collection_pointer=pointer,
        entry_ids=tuple(sorted(ids)),
        load_error=None,
    )


def detail_namespace(target_root: Path, namespace: str) -> NamespaceDetail | str:
    """Locate one namespace and return ordered (id, data) entries — or an error string."""
    summaries = summarize_schemas(target_root)
    matches = [s for s in summaries if s.name == namespace and s.is_namespace_owner]
    if not matches:
        owners = sorted({s.name for s in summaries if s.is_namespace_owner})
        avail = ", ".join(owners) if owners else "(none)"
        return (
            f"namespace {namespace!r} not found among installed capabilities. "
            f"Available namespaces: {avail}."
        )
    if len(matches) > 1:
        locs = ", ".join(f"{m.capability}/{m.name}" for m in matches)
        return (
            f"namespace {namespace!r} is ambiguous — declared in multiple "
            f"capabilities: {locs}."
        )
    summary = matches[0]
    if summary.load_error:
        return f"namespace {namespace!r}: {summary.load_error}"
    assert summary.id_collection_pointer is not None
    data = _stringify_dates(
        _yaml.load(summary.yaml_path.read_text(encoding="utf-8"))
    )
    collection = _resolve_json_pointer(data, summary.id_collection_pointer)
    entries: list[tuple[str, Any]] = []
    if isinstance(collection, dict):
        for key, value in collection.items():
            entries.append((str(key), value))
    elif isinstance(collection, list):
        for item in collection:
            if isinstance(item, dict) and "id" in item:
                entries.append((str(item["id"]), item))
    return NamespaceDetail(
        namespace=summary.name,
        capability=summary.capability,
        yaml_path=summary.yaml_path,
        companion_path=summary.companion_path,
        id_collection_pointer=summary.id_collection_pointer,
        entries=tuple(entries),
    )


def resolve_token_to_target(target_root: Path, token: str) -> TokenResolution | str:
    """Parse a typed token + locate its target entry. Returns the resolution or an error string."""
    m = _TOKEN_PATTERN.match(token)
    if m is None:
        return (
            f"not a typed token: {token!r}. Expected shape `[<namespace>:<id>]` "
            f"with both halves kebab-case."
        )
    namespace, id_value = m.group(1), m.group(2)
    detail = detail_namespace(target_root, namespace)
    if isinstance(detail, str):
        return detail
    for entry_id, entry_data in detail.entries:
        if entry_id == id_value:
            return TokenResolution(
                token=token,
                namespace=namespace,
                id=id_value,
                yaml_path=detail.yaml_path,
                companion_path=detail.companion_path,
                entry=entry_data,
            )
    known = ", ".join(eid for eid, _ in detail.entries[:8])
    suffix = (
        f" Known ids: {known}"
        + (f", ... +{len(detail.entries) - 8} more." if len(detail.entries) > 8 else ".")
        if detail.entries
        else " (namespace has no entries)."
    )
    return f"id {id_value!r} not found in namespace {namespace!r}.{suffix}"


# --- rendering (CLI helpers) ------------------------------------------


def print_schema_list(summaries: list[SchemaSummary]) -> None:
    """Render the schema list grouped by capability."""
    if not summaries:
        click.echo("  No schemas found under .pkit/capabilities/*/schemas/.")
        return
    by_cap: dict[str, list[SchemaSummary]] = {}
    for s in summaries:
        by_cap.setdefault(s.capability, []).append(s)
    click.echo()
    for cap_name in sorted(by_cap):
        click.echo("  " + cli_render.style("heading", f"capability: {cap_name}"))
        for s in sorted(by_cap[cap_name], key=lambda x: x.name):
            if s.load_error:
                click.echo(f"    {s.name:24}  ERROR: {s.load_error}")
            elif s.is_namespace_owner:
                shown = ", ".join(s.entry_ids[:6])
                suffix = (
                    f", ... +{len(s.entry_ids) - 6} more"
                    if len(s.entry_ids) > 6
                    else ""
                )
                click.echo(
                    f"    {s.name:24}  {len(s.entry_ids):>2} entr(ies): {shown}{suffix}"
                )
            else:
                click.echo(f"    {s.name:24}  (consumer — no namespace declared)")
        click.echo()


def print_namespace_detail(
    detail: NamespaceDetail, target_root: Path | None = None
) -> None:
    """Render one namespace's entries (ordered, with one-line summaries)."""
    click.echo()
    click.echo(cli_render.style("title", f"Namespace: {detail.namespace}"))
    click.echo(f"  Capability: {detail.capability}")
    click.echo(f"  YAML:       {_rel(detail.yaml_path, target_root)}")
    click.echo(f"  Companion:  {_rel(detail.companion_path, target_root)}")
    click.echo(
        f"  Collection: {detail.id_collection_pointer}  ({len(detail.entries)} entry/ies)"
    )
    click.echo()
    click.echo("  " + cli_render.style("heading", "Entries:"))
    for entry_id, entry_data in detail.entries:
        # One-line summary: pick role / description / title if present.
        summary_text = ""
        if isinstance(entry_data, dict):
            for field_name in ("role", "description", "title"):
                value = entry_data.get(field_name)
                if isinstance(value, str) and value.strip():
                    summary_text = value.strip().split("\n", 1)[0].strip()
                    break
        if summary_text:
            shown = (
                summary_text if len(summary_text) <= 70 else summary_text[:67] + "..."
            )
            click.echo(f"    {entry_id:22}  {shown}")
        else:
            click.echo(f"    {entry_id}")
    click.echo()


def print_token_resolution(
    resolution: TokenResolution, target_root: Path | None = None
) -> None:
    """Render a token-resolution result."""
    click.echo()
    click.echo(cli_render.style("title", f"Token: {resolution.token}"))
    click.echo(f"  Namespace: {resolution.namespace}")
    click.echo(f"  Id:        {resolution.id}")
    click.echo(f"  Source:    {_rel(resolution.yaml_path, target_root)}")
    click.echo()
    click.echo("  " + cli_render.style("heading", "Entry:"))
    if isinstance(resolution.entry, (dict, list)):
        from io import StringIO

        yaml_writer = YAML()
        yaml_writer.default_flow_style = False
        buf = StringIO()
        yaml_writer.dump(resolution.entry, buf)
        for line in buf.getvalue().splitlines():
            click.echo(f"    {line}")
    else:
        click.echo(f"    {resolution.entry}")
    click.echo()

