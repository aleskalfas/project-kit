"""Backbone file schemas — loading, the load-check, and container validation.

The backbone validates a class of files it does not author: the configuration
file, rule-set files, project filler files, and the methodology's block inside
an artefact's front matter (the schemas README, "Backbone file schemas and the
methodology's front-matter container"). Their schemas are propagated files
under `.pkit/schemas/backbone/`, read from the tree of the project being
validated and never from a copy in the binary (ADR-056 point 1). This module
is where that class is loaded and where its shared rendering lives:

- `backbone_schema_path` / `load_backbone_schema` — find and load one schema by
  kind (`container`, and later `config`, `rule-set`, `filler`) from a project
  root.
- `load_check` — the pass `pkit schemas validate` runs over the directory:
  every `*.schema.json` there must parse as a valid Draft 2020-12 schema
  (ADR-056 Implications). Nothing there is a YAML/companion pair, so the pair
  walk never sees these files; this is their only structural check.
- `render_unknown_key` — the one renderer every unknown-key finding of the
  class comes from (ADR-056 point 4): the offending key, the nearest known key
  by edit distance, and any reminder the owning record adds.
- `validate_container` — the container's discrimination rule (COR-053 point
  10) applied on top of the JSON Schema shape: functionality blocks by name,
  role blocks by their versioned point blocks, anything else an unknown key;
  role blocks with no active provider reported as orphans.

What is deliberately *not* here yet: provider-version compatibility of a point
block (COR-053 point 10's "inert" state) needs the role/provider resolver,
which does not exist. `resolve_point_compatibility` is the hook it will fill.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

# Where the class lives in a project tree (ADR-056 point 1), relative to root.
BACKBONE_SCHEMAS_DIR = Path(".pkit") / "schemas" / "backbone"

# The one front-matter key the methodology owns (COR-053 point 10) — this
# distribution's literal.
CONTAINER_KEY = "pkit"

# Functionality blocks shipped today, by the name that is also the command
# group (COR-050 point 1). Adding a name is a surface change checked against
# the role keys in use (COR-053 point 10).
FUNCTIONALITY_BLOCKS: frozenset[str] = frozenset({"friction"})

# The separator of a qualified role name, `<publisher>::<role>` (COR-053
# point 1).
ROLE_QUALIFIER_SEPARATOR = "::"

# The version field every point block carries (COR-052 point 5, COR-053
# point 10).
POINT_VERSION_FIELD = "schema_version"

ROLE_BLOCK_REMINDER = (
    "a role block needs a versioned point block: every child is a mapping "
    f"carrying an integer `{POINT_VERSION_FIELD}`."
)


# --- loading ----------------------------------------------------------


def backbone_schemas_dir(target_root: Path) -> Path:
    """The directory the class is read from, for the project at `target_root`."""
    return target_root / BACKBONE_SCHEMAS_DIR


def backbone_schema_path(target_root: Path, kind: str) -> Path:
    """The path of the schema for one kind (`container`, `config`, ...), present or not."""
    return backbone_schemas_dir(target_root) / f"{kind}.schema.json"


def iter_backbone_schema_paths(target_root: Path) -> list[Path]:
    """Every `*.schema.json` under the backbone directory, sorted; empty when absent."""
    schemas_dir = backbone_schemas_dir(target_root)
    if not schemas_dir.is_dir():
        return []
    return sorted(schemas_dir.glob("*.schema.json"))


def load_schema_document(schema_path: Path) -> tuple[dict | None, str | None]:
    """Read + meta-validate a JSON Schema file. Returns (schema, reason).

    Exactly one of the two is non-None. `reason` completes the sentence
    "<the file> is <reason>", so each caller names the file in the terms its
    own report uses. Shared with the pair validator, which reads companions
    the same way.
    """
    try:
        text = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"unreadable: {exc}."
    try:
        schema = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"not valid JSON: {exc.msg} at line {exc.lineno} col {exc.colno}."
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return None, f"not a valid Draft 2020-12 JSON Schema: {exc.message}"
    return schema, None


class BackboneSchemaMissing(FileNotFoundError):
    """The tree ships no schema for this kind (ADR-056 point 1: skip, never substitute)."""


class BackboneSchemaInvalid(ValueError):
    """The tree's schema for this kind does not load as a Draft 2020-12 schema."""


def load_backbone_schema(target_root: Path, kind: str) -> dict:
    """Load the schema for `kind` from the project's tree.

    Raises `BackboneSchemaMissing` when the tree lacks it — a tree recorded
    before that schema landed — so the caller can report "no schema present,
    skipped" rather than validate against a shape the tree never shipped.
    Raises `BackboneSchemaInvalid` when the file is present but malformed;
    `load_check` is where that is reported as a finding.
    """
    path = backbone_schema_path(target_root, kind)
    if not path.is_file():
        raise BackboneSchemaMissing(str(path))
    schema, reason = load_schema_document(path)
    if schema is None:
        raise BackboneSchemaInvalid(f"{path} is {reason}")
    return schema


@dataclass(frozen=True)
class LoadCheckResult:
    """Outcome of the load-check over the backbone directory."""

    checked: tuple[Path, ...]
    failures: tuple[tuple[Path, str], ...]  # (path, reason) per schema that failed to load


def load_check(target_root: Path) -> LoadCheckResult:
    """Load every schema in the backbone directory; report each that fails.

    The directory is a set of lone companions, not pairs, so it is checked by
    enumeration of `*.schema.json` — never by deriving a companion from a YAML
    half (ADR-056 Alternatives, "direct children of `.pkit/schemas/`").
    """
    paths = iter_backbone_schema_paths(target_root)
    failures: list[tuple[Path, str]] = []
    for path in paths:
        _schema, reason = load_schema_document(path)
        if reason is not None:
            failures.append((path, reason))
    return LoadCheckResult(checked=tuple(paths), failures=tuple(failures))


# --- the shared unknown-key renderer ----------------------------------


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance between two strings."""
    if a == b:
        return 0
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]


def nearest_known_key(key: str, known: Iterable[str]) -> str | None:
    """The known key closest to `key` by edit distance; ties broken alphabetically.

    None only when `known` is empty. No distance cut-off: the records ask for
    *the nearest* key, and a far suggestion next to the reminder still tells
    the reader what the known set looks like.
    """
    candidates = sorted(set(known))
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: (edit_distance(key, candidate), candidate))


def render_unknown_key(key: str, known: Iterable[str], *, reminder: str | None = None) -> str:
    """The one sentence every backbone file schema uses for an unknown key.

    `known` is the set the owning record names for that file — for the
    container, the functionality names plus the active role words and their
    qualified forms (COR-053 point 10); for the configuration file, its keys
    (COR-048 point 4). `reminder` is the record's extra clause, when it has
    one — the container adds that a role block needs a versioned point block.
    """
    known_keys = set(known)
    if key in known_keys:
        # A known name with a value that has none of the shapes it may take —
        # in the container, a role word whose children are not all versioned.
        message = f"key {key!r} is known, but its value is not the shape its kind expects."
    else:
        message = f"unknown key {key!r}"
        suggestion = nearest_known_key(key, known_keys)
        message += f"; did you mean {suggestion!r}?" if suggestion is not None else "."
    if reminder:
        message += f" Note: {reminder}"
    return message


# --- the container ----------------------------------------------------


class Severity(Enum):
    """Whether a finding fails validation or is only reported (COR-053 point 10)."""

    ERROR = "error"
    REPORT = "report"


class FindingKind(Enum):
    """What a container finding is about."""

    SHAPE = "shape"  # a JSON Schema violation inside a recognised block
    UNKNOWN_KEY = "unknown-key"  # neither a functionality block nor a role block
    ORPHANED_ROLE = "orphaned-role"  # a role block whose role has no active provider
    INERT_POINT = "inert-point"  # a point block at a version the active provider cannot read


@dataclass(frozen=True)
class ContainerFinding:
    """One finding on a carrier, located by JSON Pointer from the carrier's root."""

    location: str  # e.g. "/pkit/frictoin", "/pkit/friction/revalidated"
    kind: FindingKind
    severity: Severity
    message: str


@dataclass(frozen=True)
class ContainerReport:
    """Outcome of validating one carrier (a document's front matter or a collection entry)."""

    findings: tuple[ContainerFinding, ...]
    functionality_blocks: tuple[str, ...]  # keys recognised as functionality blocks
    role_blocks: tuple[str, ...]  # keys recognised as role blocks (active or orphaned)
    orphaned_roles: tuple[str, ...]  # the subset of role_blocks with no active provider

    @property
    def errors(self) -> tuple[ContainerFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def reports(self) -> tuple[ContainerFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.REPORT)

    @property
    def is_clean(self) -> bool:
        """No errors. Reports (orphans, inert points) do not make a carrier unclean."""
        return not self.errors


@dataclass(frozen=True)
class KnownRoles:
    """The active role set, split the way the container's rule reads it."""

    words: frozenset[str]  # bare role words usable as keys
    qualified: frozenset[str]  # `<publisher>::<role>` forms

    @classmethod
    def from_active(cls, active_roles: Collection[str]) -> KnownRoles:
        """Derive the key forms from the active roles.

        Each entry is a qualified role name `<publisher>::<role>`; a bare word
        is accepted and contributes only itself. A role word equal to a
        functionality block's name is never a valid bare key — it must be
        written qualified (COR-053 point 10, "Keys") — so it is left out of
        `words`. Qualifier resolution from the installed provider is the
        resolver's job; until it exists the caller passes the set.
        """
        words: set[str] = set()
        qualified: set[str] = set()
        for role in active_roles:
            if ROLE_QUALIFIER_SEPARATOR in role:
                qualified.add(role)
                word = role.rsplit(ROLE_QUALIFIER_SEPARATOR, 1)[1]
            else:
                word = role
            if word not in FUNCTIONALITY_BLOCKS:
                words.add(word)
        return cls(words=frozenset(words), qualified=frozenset(qualified))

    def known_keys(self) -> frozenset[str]:
        """The known set for the unknown-key suggestion (COR-053 point 10)."""
        return FUNCTIONALITY_BLOCKS | self.words | self.qualified

    def is_active(self, key: str) -> bool:
        return key in self.words or key in self.qualified


def is_point_block(value: Any) -> bool:
    """A mapping carrying an integer `schema_version` (a bool is not an integer here)."""
    if not isinstance(value, Mapping):
        return False
    version = value.get(POINT_VERSION_FIELD)
    return isinstance(version, int) and not isinstance(version, bool)


def is_role_block(value: Any) -> bool:
    """A non-empty mapping whose every child is a point block (COR-053 point 10)."""
    if not isinstance(value, Mapping) or not value:
        return False
    return all(is_point_block(child) for child in value.values())


def resolve_point_compatibility(role_key: str, point: str, schema_version: int) -> bool | None:
    """Hook: is this point block's version compatible with the active provider's point?

    Returns True (compatible), False (inert — reported, body unvalidated, per
    COR-053 point 10 and COR-052 point 5) or None when the question cannot be
    answered. The role/provider resolver does not exist yet, so every call
    returns None and `validate_container` emits no inert findings. When the
    resolver lands, this is the one function to fill; nothing else changes.
    """
    return None


def validate_container(
    carrier: Mapping[Any, Any],
    schema: Mapping[str, Any],
    *,
    active_roles: Collection[str] = (),
) -> ContainerReport:
    """Validate the container carried by `carrier` against `schema` and the rule.

    `carrier` is the parsed front matter of a document, or one collection
    entry; `schema` is the loaded container schema (`load_backbone_schema(root,
    "container")`); `active_roles` is the set of active qualified role names
    (see `KnownRoles.from_active`).

    Two layers, in order:

    1. The JSON Schema shape pass over the whole carrier. It fixes the friction
       block strictly and models any other key as a role block.
    2. The discrimination rule (COR-053 point 10) on each key of the container:
       a functionality name is that block (its shape findings are kept); a
       value that is a role block is one (active, or orphaned when its role is
       not in `active_roles` — a report, never an error); anything else is one
       unknown-key error, and the shape errors the schema raised while trying
       to read it as a role block are dropped in its favour.

    A carrier without the container key is clean with nothing recognised; the
    key written with no value (`pkit:` parses to null) is present, and the
    shape pass reports it. Date and datetime values a YAML parser produced, and
    keys it did not read as text (`2026:`, `2026-10-02:`), are rendered back to
    their written form first (a UTC datetime as `...Z`), so the schema's string
    patterns and the rule judge what the person wrote. `as_written` is public
    so the front-matter reader hands every consumer the same rendering.
    """
    carrier = as_written(carrier)
    if CONTAINER_KEY not in carrier:
        return ContainerReport(
            findings=(), functionality_blocks=(), role_blocks=(), orphaned_roles=()
        )
    container = carrier[CONTAINER_KEY]

    roles = KnownRoles.from_active(active_roles)
    shape_by_key = _shape_findings_by_container_key(carrier, schema)
    findings: list[ContainerFinding] = list(shape_by_key.pop(None, []))
    functionality: list[str] = []
    role_blocks: list[str] = []
    orphans: list[str] = []

    if not isinstance(container, Mapping):
        # The shape pass already said what is wrong at /pkit; nothing to discriminate.
        return ContainerReport(
            findings=tuple(findings),
            functionality_blocks=(),
            role_blocks=(),
            orphaned_roles=(),
        )

    for key, value in container.items():
        location = f"/{CONTAINER_KEY}/{_pointer_token(key)}"
        if key in FUNCTIONALITY_BLOCKS:
            functionality.append(key)
            findings.extend(shape_by_key.get(key, []))
            continue
        if is_role_block(value):
            role_blocks.append(key)
            findings.extend(shape_by_key.get(key, []))
            if not roles.is_active(key):
                orphans.append(key)
                findings.append(
                    ContainerFinding(
                        location=location,
                        kind=FindingKind.ORPHANED_ROLE,
                        severity=Severity.REPORT,
                        message=(
                            f"role block {key!r} has no active provider; preserved and "
                            f"validated again when a provider of the role is active."
                        ),
                    )
                )
                continue
            findings.extend(_inert_point_findings(key, value, location))
            continue
        findings.append(
            ContainerFinding(
                location=location,
                kind=FindingKind.UNKNOWN_KEY,
                severity=Severity.ERROR,
                message=render_unknown_key(key, roles.known_keys(), reminder=ROLE_BLOCK_REMINDER),
            )
        )

    return ContainerReport(
        findings=tuple(findings),
        functionality_blocks=tuple(functionality),
        role_blocks=tuple(role_blocks),
        orphaned_roles=tuple(orphans),
    )


def _inert_point_findings(
    role_key: str, role_block: Mapping[str, Any], location: str
) -> list[ContainerFinding]:
    """Ask the compatibility hook about each point block; report the inert ones."""
    findings: list[ContainerFinding] = []
    for point, block in role_block.items():
        compatible = resolve_point_compatibility(role_key, point, block[POINT_VERSION_FIELD])
        if compatible is False:
            findings.append(
                ContainerFinding(
                    location=f"{location}/{_pointer_token(point)}",
                    kind=FindingKind.INERT_POINT,
                    severity=Severity.REPORT,
                    message=(
                        f"point block {point!r} of role {role_key!r} is at "
                        f"{POINT_VERSION_FIELD} {block[POINT_VERSION_FIELD]}, which the active "
                        f"provider cannot read; inert, body unvalidated."
                    ),
                )
            )
    return findings


def _shape_findings_by_container_key(
    carrier: Mapping[str, Any], schema: Mapping[str, Any]
) -> dict[str | None, list[ContainerFinding]]:
    """Run the JSON Schema pass; group findings by the container key they fall under.

    The `None` group holds findings at or above the container itself (`/pkit`
    not a mapping, say). Sorted by position so output is stable; the sort key
    renders every segment as text because a path mixes keys with list indices.
    """
    registry = Registry().with_resource(
        uri=schema.get("$id", "container.schema.json"),
        resource=Resource.from_contents(schema, default_specification=DRAFT202012),
    )
    validator = Draft202012Validator(schema, registry=registry)
    grouped: dict[str | None, list[ContainerFinding]] = {}
    errors = sorted(validator.iter_errors(carrier), key=lambda e: [str(p) for p in e.absolute_path])
    for error in errors:
        path = list(error.absolute_path)
        key = str(path[1]) if len(path) >= 2 and path[0] == CONTAINER_KEY else None
        pointer = "/" + "/".join(_pointer_token(p) for p in path) if path else ""
        grouped.setdefault(key, []).append(
            ContainerFinding(
                location=pointer,
                kind=FindingKind.SHAPE,
                severity=Severity.ERROR,
                message=error.message,
            )
        )
    return grouped


def as_written(obj: Any) -> Any:
    """Render parsed values — and mapping keys — back to the form written in the file.

    YAML's `2026-10-02T09:40:12Z` parses to an aware datetime; the schema's
    `utc-timestamp` pattern wants the written `Z` form, and `isoformat()` would
    give `+00:00`. A UTC datetime renders as `...Z`, keeping any fractional
    seconds so `...12.5Z` still fails the pattern as the written text would; a
    date as ISO; a datetime in another zone keeps `isoformat()` and so fails
    the pattern, which is right — the record asks for UTC. Not recoverable: a
    space-separated `2026-10-02 09:40:12Z` parses to the same datetime as the
    `T` form and is accepted. Other values pass through unchanged.

    Mapping keys are rendered too: YAML reads `2026:` as an integer and
    `2026-10-02:` as a date, while JSON Schema and the container's rule know
    only text keys. Every key downstream — grouping, lookup, the edit-distance
    suggestion — is therefore a string.
    """
    if isinstance(obj, Mapping):
        return {_key_as_written(k): as_written(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [as_written(x) for x in obj]
    if isinstance(obj, datetime):
        if obj.tzinfo is not None and obj.utcoffset() == timedelta(0):
            seconds = obj.strftime("%Y-%m-%dT%H:%M:%S")
            fraction = f".{obj.microsecond:06d}".rstrip("0") if obj.microsecond else ""
            return f"{seconds}{fraction}Z"
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def _key_as_written(key: Any) -> str:
    """A mapping key as text: unchanged when already text, else its written form."""
    return key if isinstance(key, str) else str(as_written(key))


def _pointer_token(segment: Any) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return str(segment).replace("~", "~0").replace("/", "~1")
