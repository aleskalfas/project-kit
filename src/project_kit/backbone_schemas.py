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
  by edit distance, and any reminder the owning record adds. `unknown_keys`
  and `expand_schema_error` route a JSON Schema validator's
  `additionalProperties` violation through it, one finding per key, so every
  pass that validates against a schema phrases the finding the same way.
- `filler_subpath` / `filler_address` — the filler path location rule (ADR-056
  point 2): a point address `<publisher>::<role>:<point>` maps to
  `<publisher>/<role>/<point>.yaml` under the backbone's sub-path of the
  internal documentation root, `FILLERS_SUBPATH`, and back — injective on valid
  addresses, whose parts are words (the lifecycle README, "Where a project
  filler file lives"). `envelope_findings` applies the filler envelope's
  schema (kind `filler`) through the shared renderer.
- `validate_container` — the container's discrimination rule (COR-053 point
  10) applied on top of the JSON Schema shape: functionality blocks by name,
  role blocks by their versioned point blocks, anything else an unknown key.
  What it knows of the roles and points comes from the resolved wiring, handed
  in as a `ContainerWiring` (`connections.container_wiring` builds it from the
  run's one resolution): a role block whose role has no active provider is
  reported as an orphan; a point block at another version than the active
  provider's point, or naming no data point that provider defines, is reported
  as inert with its body unvalidated (`resolve_point_compatibility`); a
  compatible one is validated by the provider's point schema.

This module reads no package metadata and resolves no wiring: it is below the
resolver, which imports it.
"""

from __future__ import annotations

import json
import re
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
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
# point 1), and of the point in an address `<publisher>::<role>:<point>`
# (point 2).
ROLE_QUALIFIER_SEPARATOR = "::"
POINT_SEPARATOR = ":"

# A part of a role or point address: a word, the words the configuration's
# selection keys admit. The one definition of the address word — `refs`
# re-exports it for the citation grammar, and the package and configuration
# schemas spell it in their address patterns.
ADDRESS_WORD_PATTERN = "[a-z][a-z0-9-]*"

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


def unknown_keys(error: ValidationError) -> list[str]:
    """The keys an `additionalProperties` violation is about — every key of the
    instance mapping that neither `properties` nor `patternProperties` admits —
    sorted, so one finding per key is deterministic. Empty for any other error.
    """
    if error.validator != "additionalProperties" or not isinstance(error.instance, Mapping):
        return []
    known = set((error.schema.get("properties") or {}).keys())
    patterns = list((error.schema.get("patternProperties") or {}).keys())
    return sorted(
        str(key)
        for key in error.instance
        if key not in known and not any(re.search(pattern, str(key)) for pattern in patterns)
    )


def expand_schema_error(error: ValidationError) -> list[tuple[tuple[str, ...], str]]:
    """One `(path segments, message)` per violation, an `additionalProperties`
    error over a mapping expanded to one per unknown key and rendered by
    `render_unknown_key` from the schema's known keys (ADR-056 point 4). Any
    other error keeps the validator's own message.
    """
    path = tuple(str(segment) for segment in error.absolute_path)
    keys = unknown_keys(error)
    if not keys:
        return [(path, error.message)]
    known = tuple((error.schema.get("properties") or {}).keys())
    return [((*path, key), render_unknown_key(key, known)) for key in keys]


# --- the filler path and the filler envelope (ADR-056 point 2) ---------------

# The sub-path the backbone owns for filler files under the internal
# documentation root (COR-052 point 2) — this distribution's literal, the
# lifecycle README's third.
FILLERS_SUBPATH = PurePosixPath("pkit") / "fillers"

# The kind the envelope's schema is read under (`load_backbone_schema`).
FILLER_SCHEMA_KIND = "filler"

# A filler file's suffix: the one dot of the path.
FILLER_SUFFIX = ".yaml"

# A part of a valid address, whole.
_WORD = re.compile(rf"^{ADDRESS_WORD_PATTERN}$")


def filler_subpath(address: str) -> PurePosixPath | None:
    """The path of the filler for `address`, relative to the fillers prefix:
    `<publisher>/<role>/<point>.yaml`; None when the address is not valid —
    three parts, each a word — and so has no filler path."""
    publisher, sep, rest = address.partition(ROLE_QUALIFIER_SEPARATOR)
    role, colon, point = rest.partition(POINT_SEPARATOR)
    parts = (publisher, role, point)
    if not sep or not colon or not all(_WORD.match(part) for part in parts):
        return None
    return PurePosixPath(publisher, role, f"{point}{FILLER_SUFFIX}")


def filler_address(subpath: str) -> str | None:
    """The inverse: the address a path relative to the fillers prefix names, or
    None when it names none — not exactly three parts, a part that is not a
    word, or another suffix. `filler_subpath` sends the address back to the
    same path, so the two are inverse on valid addresses."""
    if not subpath.endswith(FILLER_SUFFIX):
        return None
    parts = subpath[: -len(FILLER_SUFFIX)].split("/")
    if len(parts) != 3 or not all(_WORD.match(part) for part in parts):
        return None
    publisher, role, point = parts
    return point_address(f"{publisher}{ROLE_QUALIFIER_SEPARATOR}{role}", point)


def envelope_findings(document: Any, schema: Mapping[str, Any]) -> list[tuple[str, str]]:
    """`(JSON Pointer, message)` per violation of the filler envelope's schema,
    by position; an unknown key reads through the shared renderer. The value
    inside is the point's to judge, not this schema's."""
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda e: [str(p) for p in e.absolute_path])
    return [
        ("".join(f"/{_pointer_token(p)}" for p in path), message)
        for error in errors
        for path, message in expand_schema_error(error)
    ]


# --- the container ----------------------------------------------------


class Severity(Enum):
    """Whether a finding fails validation or is only reported (COR-053 point 10)."""

    ERROR = "error"
    REPORT = "report"


class FindingKind(Enum):
    """What a container finding is about."""

    SHAPE = "shape"  # a JSON Schema violation inside a recognised block, or a point body
    UNKNOWN_KEY = "unknown-key"  # neither a functionality block nor a role block
    AMBIGUOUS_ROLE = "ambiguous-role"  # a bare role word two or more active roles share
    ORPHANED_ROLE = "orphaned-role"  # a role block whose role has no active provider
    INERT_POINT = "inert-point"  # a point block the active provider's point does not match
    POINT_SCHEMA_UNAVAILABLE = "point-schema-unavailable"  # the provider's point schema is unreadable


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


# --- what the container reads of the wiring ----------------------------


@dataclass(frozen=True)
class ActivePoint:
    """A data point an active role's provider defines, as a point block reads it.

    `validator` checks a point block's body against the provider's point
    schema; when the schema could not be loaded it is None and `unavailable`
    says why.
    """

    version: int
    validator: Draft202012Validator | None = field(default=None, compare=False)
    unavailable: str | None = None


@dataclass(frozen=True)
class ContainerWiring:
    """What container validation reads from the resolved wiring (COR-053 points 7 and 10).

    `providers` maps each qualified role with an active provider to that
    provider; `points` maps the address `<publisher>::<role>:<point>` of every
    data point those providers define to what a point block needs of it. The
    resolver computes both (`connections.container_wiring`); the empty value has
    no active role, so every role block reads as orphaned.
    """

    providers: Mapping[str, str] = field(default_factory=dict[str, str])
    points: Mapping[str, ActivePoint] = field(default_factory=dict[str, ActivePoint])

    def points_of(self, role: str) -> tuple[str, ...]:
        """The names of the data points `role`'s active provider defines, sorted."""
        prefix = point_address(role, "")
        return tuple(sorted(a[len(prefix) :] for a in self.points if a.startswith(prefix)))


def point_address(role: str, point: str) -> str:
    """`<publisher>::<role>:<point>` (COR-053 point 2)."""
    return f"{role}{POINT_SEPARATOR}{point}"


@dataclass(frozen=True)
class KnownRoles:
    """The active role set, split the way the container's rule reads it."""

    words: frozenset[str]  # bare role words usable as keys: each names one active role
    qualified: frozenset[str]  # `<publisher>::<role>` forms
    roles_of_word: Mapping[str, tuple[str, ...]]  # every active role a bare word names, sorted

    @classmethod
    def from_active(cls, active_roles: Collection[str]) -> KnownRoles:
        """Derive the key forms from the active roles.

        Each entry is a qualified role name `<publisher>::<role>`; a bare word
        is accepted and contributes only itself. A role word equal to a
        functionality block's name, or shared by two active roles, is never a
        valid bare key — it must be written qualified (COR-053 point 10,
        "Keys") — so it is left out of `words`.
        """
        roles_of_word: dict[str, list[str]] = {}
        qualified: set[str] = set()
        for role in sorted(active_roles):
            if ROLE_QUALIFIER_SEPARATOR in role:
                qualified.add(role)
                word = role.rsplit(ROLE_QUALIFIER_SEPARATOR, 1)[1]
            else:
                word = role
            if word not in FUNCTIONALITY_BLOCKS:
                roles_of_word.setdefault(word, []).append(role)
        return cls(
            words=frozenset(w for w, roles in roles_of_word.items() if len(roles) == 1),
            qualified=frozenset(qualified),
            roles_of_word={w: tuple(roles) for w, roles in roles_of_word.items()},
        )

    def known_keys(self) -> frozenset[str]:
        """The known set for the unknown-key suggestion (COR-053 point 10)."""
        return FUNCTIONALITY_BLOCKS | self.words | self.qualified

    def role_of(self, key: str) -> str | None:
        """The active role a key names: the key itself when qualified, the one
        active role of its word when bare; None when it names none, or several."""
        if key in self.qualified:
            return key
        if key in self.words:
            return self.roles_of_word[key][0]
        return None

    def sharing(self, key: str) -> tuple[str, ...]:
        """The active roles a bare key's word belongs to, when two or more share it."""
        roles = self.roles_of_word.get(key, ())
        return roles if len(roles) > 1 else ()


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


class PointCompatibility(Enum):
    """How a point block stands against its role's active provider (COR-053 point 10)."""

    COMPATIBLE = "compatible"  # the provider defines the point at the block's version
    OTHER_VERSION = "other version"  # defined at another version: inert
    UNDEFINED = "undefined"  # the provider defines no such data point: inert


def resolve_point_compatibility(
    wiring: ContainerWiring, role: str, point: str, schema_version: int
) -> PointCompatibility:
    """The compatibility hook: is a point block of the active role `role` readable
    by its provider?

    Compatible when the provider defines the data point and the integers are
    equal — the rule the resolver applies to every counterpart (COR-053 point
    5). Anything else is inert: reported, the body left unvalidated, as an
    out-of-step filler is (COR-052 point 5). A point the provider does not
    define is inert rather than an error, as a filler whose point has no active
    provider is (ADR-056 point 2): the data is the project's, and may be read
    again by a later provider.
    """
    active = wiring.points.get(point_address(role, point))
    if active is None:
        return PointCompatibility.UNDEFINED
    if active.version != schema_version:
        return PointCompatibility.OTHER_VERSION
    return PointCompatibility.COMPATIBLE


def validate_container(
    carrier: Mapping[Any, Any],
    schema: Mapping[str, Any],
    *,
    wiring: ContainerWiring | None = None,
) -> ContainerReport:
    """Validate the container carried by `carrier` against `schema`, the rule and the wiring.

    `carrier` is the parsed front matter of a document, or one collection
    entry; `schema` is the loaded container schema (`load_backbone_schema(root,
    "container")`); `wiring` is what the resolved wiring says of the active
    roles and their data points (`ContainerWiring`; none means no active role).

    Two layers, in order:

    1. The JSON Schema shape pass over the whole carrier. It fixes the friction
       block strictly and models any other key as a role block.
    2. The discrimination rule (COR-053 point 10) on each key of the container:
       a functionality name is that block (its shape findings are kept); a
       value that is a role block is one; anything else is one unknown-key
       error, and the shape errors the schema raised while trying to read it as
       a role block are dropped in its favour. A role block's key then names
       its role: a qualified key itself, a bare word the one active role of
       that word. A word several active roles share is an error — the key must
       be written qualified; a role with no active provider is an orphan — a
       report, never an error; an active role's point blocks are each
       compatible, and their bodies validated by the provider's point schema,
       or inert — a report, the body unvalidated.

    A carrier without the container key is clean with nothing recognised; the
    key written with no value (`pkit:` parses to null) is present, and the
    shape pass reports it. Date and datetime values a YAML parser produced, and
    keys it did not read as text (`2026:`, `2026-10-02:`), are rendered back to
    their written form first (a UTC datetime as `...Z`), so the schema's string
    patterns, the rule and the point schemas judge what the person wrote.
    `as_written` is public so the front-matter reader hands every consumer the
    same rendering.
    """
    carrier = as_written(carrier)
    if CONTAINER_KEY not in carrier:
        return ContainerReport(
            findings=(), functionality_blocks=(), role_blocks=(), orphaned_roles=()
        )
    container = carrier[CONTAINER_KEY]

    wiring = wiring if wiring is not None else ContainerWiring()
    roles = KnownRoles.from_active(wiring.providers.keys())
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
            sharing = roles.sharing(key)
            role = roles.role_of(key)
            if sharing:
                findings.append(
                    ContainerFinding(
                        location=location,
                        kind=FindingKind.AMBIGUOUS_ROLE,
                        severity=Severity.ERROR,
                        message=(
                            f"role key {key!r} is the word of several active roles "
                            f"({_quoted(sharing)}); write the qualified key of the role this "
                            f"block belongs to (COR-053 point 10)."
                        ),
                    )
                )
            elif role is None:
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
            else:
                findings.extend(_point_findings(key, role, value, location, wiring))
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


def _point_findings(
    key: str, role: str, role_block: Mapping[str, Any], location: str, wiring: ContainerWiring
) -> list[ContainerFinding]:
    """Each point block of an active role: inert and reported, or its body validated."""
    provider = wiring.providers[role]
    findings: list[ContainerFinding] = []
    for point, block in role_block.items():
        point_location = f"{location}/{_pointer_token(point)}"
        version = block[POINT_VERSION_FIELD]
        address = point_address(role, point)
        standing = resolve_point_compatibility(wiring, role, point, version)
        if standing is PointCompatibility.COMPATIBLE:
            findings.extend(
                _body_findings(address, provider, wiring.points[address], block, point_location)
            )
            continue
        if standing is PointCompatibility.OTHER_VERSION:
            problem = (
                f"is at {POINT_VERSION_FIELD} {version}, but {provider!r} defines {address!r} "
                f"at version {wiring.points[address].version}"
            )
        else:
            defined = wiring.points_of(role)
            problem = (
                f"names no data point {provider!r} defines for {role!r} "
                + (f"(it defines: {_quoted(defined)})" if defined else "(it defines none)")
            )
        findings.append(
            ContainerFinding(
                location=point_location,
                kind=FindingKind.INERT_POINT,
                severity=Severity.REPORT,
                message=(
                    f"point block {point!r} of role block {key!r} {problem}; inert, body "
                    f"unvalidated (COR-053 point 10)."
                ),
            )
        )
    return findings


def _body_findings(
    address: str, provider: str, active: ActivePoint, block: Mapping[str, Any], location: str
) -> list[ContainerFinding]:
    """A compatible point block's body — everything but `schema_version` — against
    the provider's point schema. An unknown key reads through the shared renderer."""

    def cannot_apply(reason: str) -> list[ContainerFinding]:
        return [
            ContainerFinding(
                location=location,
                kind=FindingKind.POINT_SCHEMA_UNAVAILABLE,
                severity=Severity.REPORT,
                message=(
                    f"the point schema {provider!r} ships for {address!r} cannot be applied "
                    f"({reason}); body unvalidated."
                ),
            )
        ]

    if active.validator is None:
        return cannot_apply(active.unavailable or "it was not loaded")
    body = {k: v for k, v in block.items() if k != POINT_VERSION_FIELD}
    try:
        errors = sorted(
            active.validator.iter_errors(body), key=lambda e: [str(p) for p in e.absolute_path]
        )
    except Unresolvable as exc:
        return cannot_apply(f"a `$ref` in it does not resolve: {exc.ref!r}")
    return [
        ContainerFinding(
            location=location + "".join(f"/{_pointer_token(p)}" for p in path),
            kind=FindingKind.SHAPE,
            severity=Severity.ERROR,
            message=f"{message} ({provider!r}'s point schema for {address!r})",
        )
        for error in errors
        for path, message in expand_schema_error(error)
    ]


def _quoted(names: Iterable[str]) -> str:
    return ", ".join(repr(n) for n in names)


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
