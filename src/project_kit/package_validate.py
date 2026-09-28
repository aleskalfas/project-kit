"""Package metadata validation — one `package.yaml` against the package schema,
plus the repository checks the schema cannot express.

Every installed component's `package.yaml` validates against one shared
backbone file schema, `.pkit/schemas/backbone/package.schema.json` (ADR-056):
the fields the shipped package files use today plus the blocks the newer
records add — `connections` (COR-053 point 3), `docs.locations` (COR-049 point
4), `friction.places` / `friction.surface` (COR-050 points 1 and 8). Three
passes, in order, each producing findings located by JSON Pointer:

1. **Shape** — the JSON Schema pass. Known keys are strictly typed; a
   violation is an ERROR.
2. **Unknown keys** — the schema is permissive (`additionalProperties` open)
   so an unknown key is not a schema error. This pass walks the instance
   alongside the schema and reports each key that no `properties` entry names
   as a WARNING carrying the nearest known key, through the one renderer of
   the class (`backbone_schemas.render_unknown_key`). Refusing unknown keys is
   Task #999's flip; until then warnings never fail a check.
3. **Repository checks** — what needs the tree, not just the file: the
   component's name matches its directory, versions and ranges parse, every
   command script exists, a declared point sits under a provided role, an
   accepted data point's companion schema exists under `schemas/`, every
   filler / emitter / subscriber command exists in `commands:`, every filler
   command and every validator's command declares the query contract
   (`query-contract: true`, ADR-057 point 3 and ADR-058), a contribution
   names `command` or `value` but not both, documentation locations are
   relative sub-paths, friction places lie inside a declared location or the
   project, and the generated `depends-on` list says what the component's
   process definitions generate (`process_dependencies.staleness`, COR-053
   point 4) — a stale copy names `pkit capabilities refresh <name>` as the
   fix. All ERRORs.

The checks across packages — roles and their providers, counterparts against
point versions, mandatory marks and cycles, fingerprints, the version
relations — are the wiring resolver's (`connections`, COR-053 point 7).
`check_wiring` hands the pass the resolved `Wiring`, whose errors join the
issue list and which `pkit validate` shows under its "connections" and
"versions" headings; `resolve_active_roles` answers which qualified roles have
an active provider.

Two callers: `pkit validate` runs `validate_installed_packages` over every
component the backbone manifest registers (the "packages" pass), and the
install-time self-consistency check of an incubated capability
(`capabilities.validate_capability_self_consistency`) runs `validate_package`
on the one capability it is about to activate. Same code, same messages.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any

from jsonschema import Draft202012Validator
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML

from project_kit import process_dependencies, validators
from project_kit.backbone_schemas import (
    BackboneSchemaMissing,
    load_backbone_schema,
    render_unknown_key,
)
from project_kit.command_runner import command_leaves, resolve_command
from project_kit.manifest import read_backbone_manifest
from project_kit.validators import COMMAND_KEY, QUERY_CONTRACT_KEY, VALIDATORS_KEY

if TYPE_CHECKING:
    from project_kit.connections import Wiring

# The kind under which the schema is read from the tree (`load_backbone_schema`).
SCHEMA_KIND = "package"

# Where a component of each kind lives in a project tree, relative to `.pkit/`.
_COMPONENT_DIRS = {"capability": "capabilities", "adapter": "adapters"}

# The separator of a qualified role, and of the point inside an address
# `<publisher>::<role>:<point>` (COR-053 points 1 and 2).
ROLE_QUALIFIER = "::"
POINT_SEPARATOR = ":"

_yaml = YAML(typ="safe")


class Severity(Enum):
    """Whether a finding fails the check. Warnings never do (the permissive posture)."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class PackageFinding:
    """One finding on a package file, located by JSON Pointer from the document root."""

    path: str  # e.g. "/component/version", "/commands/validate/script"; "" for the root
    severity: Severity
    message: str


@dataclass(frozen=True)
class PackageReport:
    """Outcome of validating one package file."""

    file: Path
    findings: tuple[PackageFinding, ...]

    @property
    def errors(self) -> tuple[PackageFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[PackageFinding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.WARNING)

    @property
    def is_clean(self) -> bool:
        """No errors. Warnings do not make a package unclean."""
        return not self.errors


# --- the wiring resolver (COR-053 point 7) -------------------------------


def resolve_active_roles(target_root: Path) -> frozenset[str]:
    """The qualified roles with one active provider in this project: one installed
    provider, or the one the provider-selection key names (COR-053 point 1)."""
    from project_kit import connections  # the resolver imports this module's types

    return connections.resolve_wiring(target_root).active_roles()


def check_wiring(target_root: Path) -> Wiring:
    """The cross-package checks, as the resolved wiring: role conflicts, counterpart
    version compatibility, unmet mandatory marks and cycles, fingerprint
    disagreements, version relations (COR-053 points 1, 5 and 6; COR-030). Its
    findings are located in the package files (or the configuration file, when
    the fix is a selection entry)."""
    from project_kit import connections

    return connections.resolve_wiring(target_root)


# --- one package file --------------------------------------------------


def validate_package_file(
    path: Path,
    schema: Mapping[str, Any] | None,
    *,
    component_dir: Path | None = None,
    expected_name: str | None = None,
) -> PackageReport:
    """Read and validate one package file. See `validate_package` for the passes.

    A file that does not parse as a YAML mapping is one error at the root.
    """
    try:
        raw = _yaml.load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # ruamel raises its own hierarchy; the message is what matters
        return PackageReport(
            file=path,
            findings=(PackageFinding("", Severity.ERROR, f"not valid YAML: {exc}"),),
        )
    if not isinstance(raw, Mapping):
        return PackageReport(
            file=path,
            findings=(
                PackageFinding(
                    "", Severity.ERROR, f"expected a mapping at the top level, got {_kind(raw)}."
                ),
            ),
        )
    findings = validate_package(
        raw,
        schema,
        component_dir=component_dir if component_dir is not None else path.parent,
        expected_name=expected_name,
    )
    return PackageReport(file=path, findings=tuple(findings))


def validate_package(
    raw: Mapping[Any, Any],
    schema: Mapping[str, Any] | None,
    *,
    component_dir: Path,
    expected_name: str | None = None,
) -> list[PackageFinding]:
    """Validate a parsed package mapping: shape, unknown keys, repository checks.

    `schema` is the loaded package schema (`load_backbone_schema(root,
    "package")`), or None when the tree ships none — then only the repository
    checks run, which cover every check the install-time check ran before the
    schema existed, and more (ADR-056 point 1: never validate against a shape
    the tree never shipped). `component_dir` is the component's root, where
    `scripts` and `schemas/` are resolved; `expected_name` is the directory
    name the component must match, when the caller knows it.

    One location is reported by one pass: a later pass never adds a finding
    where an earlier one already stands (a key whose type the shape pass
    rejected is not also warned about or re-checked). Within a pass every
    finding is kept — two missing required keys are two errors at one location.
    """
    findings: list[PackageFinding] = []
    if schema is not None:
        schema_id = schema.get("$id", "package.schema.json")
        registry = Registry().with_resource(
            uri=schema_id,
            resource=Resource.from_contents(schema, default_specification=DRAFT202012),
        )
        validator = Draft202012Validator(schema, registry=registry)
        _add_pass(
            findings,
            (
                PackageFinding(_pointer(error.absolute_path), Severity.ERROR, error.message)
                for error in sorted(
                    validator.iter_errors(raw), key=lambda e: _sort_key(e.absolute_path)
                )
            ),
        )
        walker = _UnknownKeyWalker(validator)
        _add_pass(findings, walker.walk(raw, schema, registry.resolver(base_uri=schema_id), ""))
    _add_pass(findings, _repository_findings(raw, component_dir, expected_name))
    return findings


def _add_pass(findings: list[PackageFinding], new: Iterable[PackageFinding]) -> None:
    """Append one pass's findings, skipping every location an earlier pass reported."""
    located = {f.path for f in findings}
    findings.extend(f for f in new if f.path not in located)


# --- pass 2: unknown keys ---------------------------------------------


class _UnknownKeyWalker:
    """Walk an instance alongside its schema; warn on each key no `properties` entry names.

    Only the keywords the package schema uses are followed: `$ref`, `allOf`,
    `if`/`then`/`else`, `properties`, `additionalProperties`, `items`. An
    object whose schema declares no `properties` (a map keyed by point
    address, say) has no known set to judge against and yields nothing; an
    object whose `additionalProperties` is itself a schema has its extra keys
    validated by that schema, not judged here; `additionalProperties: false`
    is the shape pass's business. The shape pass's validator is kept so an
    `if` condition is evaluated through it, against the resolver in hand — a
    `$ref` inside an `if` resolves from the same base as everywhere else, not
    from the condition treated as a root.
    """

    def __init__(self, validator: Draft202012Validator) -> None:
        self.validator = validator

    def walk(self, instance: Any, schema: Any, resolver: Any, pointer: str) -> list[PackageFinding]:
        if not isinstance(schema, Mapping):
            return []
        findings: list[PackageFinding] = []

        if "$ref" in schema:
            resolved = resolver.lookup(schema["$ref"])
            findings.extend(self.walk(instance, resolved.contents, resolved.resolver, pointer))
        for sub in schema.get("allOf", ()):
            findings.extend(self.walk(instance, sub, resolver, pointer))
        if "if" in schema:
            holds = not any(self.validator.descend(instance, schema["if"], resolver=resolver))
            branch = "then" if holds else "else"
            if branch in schema:
                findings.extend(self.walk(instance, schema[branch], resolver, pointer))

        if isinstance(instance, Mapping):
            properties = schema.get("properties")
            additional = schema.get("additionalProperties", True)
            for key, value in instance.items():
                child = f"{pointer}/{_token(key)}"
                if properties is not None and key in properties:
                    findings.extend(self.walk(value, properties[key], resolver, child))
                elif isinstance(additional, Mapping):
                    findings.extend(self.walk(value, additional, resolver, child))
                elif additional is True and properties:
                    findings.append(
                        PackageFinding(
                            child,
                            Severity.WARNING,
                            render_unknown_key(str(key), (str(k) for k in properties)),
                        )
                    )
        elif isinstance(instance, list) and isinstance(schema.get("items"), Mapping):
            for index, item in enumerate(instance):
                findings.extend(self.walk(item, schema["items"], resolver, f"{pointer}/{index}"))
        return findings


# --- pass 3: repository checks ----------------------------------------


def _repository_findings(
    raw: Mapping[Any, Any], component_dir: Path, expected_name: str | None
) -> list[PackageFinding]:
    """The checks that need the tree or a parser the schema lacks.

    Each check reads its own slice defensively — a slice the shape pass
    already rejected is skipped (and `validate_package` drops what a later pass
    reports at a location an earlier one did). Without a schema this pass is
    the whole check, so it also refuses what the schema would have: a missing
    or empty `component.version`.
    """
    findings: list[PackageFinding] = []
    _error = _error_appender(findings)

    component = raw.get("component")
    if isinstance(component, Mapping):
        name = component.get("name")
        if expected_name is not None and isinstance(name, str) and name != expected_name:
            _error(
                "/component/name",
                f"package.yaml component.name {name!r} does not match the "
                f"capability directory name {expected_name!r}.",
            )
        version = component.get("version")
        if version is None or version == "":
            # An absent key is located at its parent — the pointer that exists,
            # and where the shape pass locates a `required` failure.
            _error(
                "/component" if version is None else "/component/version",
                "package.yaml is missing component.version.",
            )
        elif isinstance(version, str):
            try:
                Version(version)
            except InvalidVersion:
                _error(
                    "/component/version",
                    f"package.yaml component.version {version!r} is not a "
                    "valid version (it gates dependency edges).",
                )

    requires_backbone = raw.get("requires_backbone")
    if isinstance(requires_backbone, str) and requires_backbone:
        try:
            SpecifierSet(requires_backbone)
        except InvalidSpecifier:
            _error(
                "/requires_backbone",
                f"requires_backbone {requires_backbone!r} is not a valid version specifier.",
            )

    dependencies = raw.get("requires_capabilities")
    if isinstance(dependencies, list):
        for index, dep in enumerate(dependencies):
            if not isinstance(dep, Mapping):
                continue
            dep_range = dep.get("version")
            if isinstance(dep_range, str) and dep_range:
                try:
                    SpecifierSet(dep_range)
                except InvalidSpecifier:
                    _error(
                        f"/requires_capabilities/{index}/version",
                        f"requires_capabilities entry for {dep.get('name')!r} has an invalid "
                        f"version range {dep_range!r}.",
                    )

    for key in ("footprint", "runtime_ignore"):
        values = raw.get(key)
        if isinstance(values, list):
            for index, value in enumerate(values):
                _check_relative(findings, f"/{key}/{index}", value, "a repository-relative path")

    commands = raw.get("commands")
    leaves = command_leaves(commands) if isinstance(commands, Mapping) else {}
    for tokens, leaf in leaves.items():
        script = leaf.get("script")
        path = "/commands/" + "/".join(_token(t) for t in tokens) + "/script"
        relative = _check_relative(findings, path, script, "a path relative to the component root")
        if relative and not (component_dir / str(script)).is_file():
            _error(
                path,
                f"command {' '.join(tokens)!r} names script {script!r}, which does not "
                f"exist under {component_dir.name}/.",
            )

    registered = raw.get(VALIDATORS_KEY)
    if isinstance(registered, Mapping):
        for name, spec in registered.items():
            if not isinstance(spec, Mapping):
                continue
            reference = spec.get(COMMAND_KEY)
            if not isinstance(reference, str):
                continue  # the shape pass reports the type
            path = f"/{VALIDATORS_KEY}/{_token(name)}/{COMMAND_KEY}"
            leaf = resolve_command(leaves, reference)
            if leaf is None:
                _error(path, f"validator {name!r}: {undeclared_command(reference, leaves)}")
            elif leaf.get(QUERY_CONTRACT_KEY) is not True:
                _error(
                    path,
                    f"validator {name!r} names command {reference!r}, which does not declare "
                    f"the query contract (`{QUERY_CONTRACT_KEY}: true` on its `commands:` entry).",
                )

    connections = raw.get("connections")
    if isinstance(connections, Mapping):
        findings.extend(_connection_findings(connections, component_dir, leaves))

    # The generated `depends-on` list against the process definitions it is
    # generated from (COR-053 point 4): whether or not the package declares a
    # `connections` block, since a definition's `depends_on` needs one.
    stale = process_dependencies.staleness(raw, component_dir)
    if stale is not None:
        _error(stale.pointer, stale.message(_component_name(raw, expected_name, component_dir)))

    location_names: set[str] = set()
    docs = raw.get("docs")
    if isinstance(docs, Mapping) and isinstance(docs.get("locations"), Mapping):
        for name, location in docs["locations"].items():
            location_names.add(str(name))
            if isinstance(location, Mapping):
                _check_relative(
                    findings,
                    f"/docs/locations/{_token(name)}/path",
                    location.get("path"),
                    "a sub-path relative to a documentation root",
                )

    friction = raw.get("friction")
    if isinstance(friction, Mapping):
        places = friction.get("places")
        if isinstance(places, list):
            for index, place in enumerate(places):
                if not isinstance(place, Mapping):
                    continue
                _check_relative(
                    findings,
                    f"/friction/places/{index}/path",
                    place.get("path"),
                    "a path relative to its location or the project",
                )
                location = place.get("location")
                if isinstance(location, str) and location not in location_names:
                    declared = f" (declared: {sorted(location_names)})." if location_names else "."
                    _error(
                        f"/friction/places/{index}/location",
                        f"place names location {location!r}, which `docs.locations` does not "
                        f"declare{declared}",
                    )
        surface = friction.get("surface")
        if isinstance(surface, list):
            for index, value in enumerate(surface):
                _check_relative(
                    findings, f"/friction/surface/{index}", value, "a repository-relative path"
                )

    return findings


def _connection_findings(
    connections: Mapping[Any, Any],
    component_dir: Path,
    command_leaves: Mapping[tuple[str, ...], Mapping[Any, Any]],
) -> list[PackageFinding]:
    """The `connections` block against the roles it provides, its `schemas/` and `commands:`."""
    findings: list[PackageFinding] = []
    _error = _error_appender(findings)

    roles_raw = connections.get("roles")
    roles = {r for r in roles_raw if isinstance(r, str)} if isinstance(roles_raw, list) else set()

    def check_companion(path: str, schema_ref: Any) -> None:
        relative = _check_relative(findings, path, schema_ref, "a path relative to schemas/")
        if relative and not (component_dir / "schemas" / str(schema_ref)).is_file():
            _error(
                path,
                f"companion schema {schema_ref!r} does not exist under "
                f"{component_dir.name}/schemas/.",
            )

    def check_command(path: str, reference: Any) -> None:
        if not isinstance(reference, str):
            return
        problem = undeclared_command(reference, command_leaves)
        if problem is not None:
            _error(path, problem)

    points = connections.get("extension-points")
    if isinstance(points, Mapping):
        for group in ("accepts", "offers"):
            declared = points.get(group)
            if not isinstance(declared, Mapping):
                continue
            for address, point in declared.items():
                path = f"/connections/extension-points/{group}/{_token(address)}"
                role = role_of(str(address))
                if role is not None and role not in roles:
                    provided = (
                        f" (connections.roles: {sorted(roles)})."
                        if roles
                        else " (connections.roles is empty)."
                    )
                    _error(
                        path,
                        f"point {address!r} is declared under role {role!r}, which this package "
                        f"does not provide{provided}",
                    )
                if not isinstance(point, Mapping):
                    continue
                if group == "accepts":
                    check_companion(f"{path}/schema", point.get("schema"))
                elif point.get("kind") == "event":
                    check_companion(f"{path}/schema", point.get("schema"))
                    check_command(f"{path}/command", point.get("command"))

    extensions = connections.get("extensions")
    if isinstance(extensions, Mapping):
        for group in ("contributes", "subscribes"):
            entries = extensions.get(group)
            if not isinstance(entries, list):
                continue
            for index, entry in enumerate(entries):
                if not isinstance(entry, Mapping):
                    continue
                path = f"/connections/extensions/{group}/{index}"
                if "command" in entry:
                    check_command(f"{path}/command", entry["command"])
                    filler = entry["command"] if group == "contributes" else None
                    leaf = resolve_command(command_leaves, filler) if isinstance(filler, str) else None
                    if leaf is not None and leaf.get(QUERY_CONTRACT_KEY) is not True:
                        _error(
                            f"{path}/command",
                            f"the contribution to {entry.get('point')!r} names command "
                            f"{filler!r} as its filler, which does not declare the query "
                            f"contract (`{QUERY_CONTRACT_KEY}: true` on its `commands:` entry); "
                            f"a command filler runs only when it declares it (COR-052 point 6).",
                        )
                if group == "contributes" and "command" in entry and "value" in entry:
                    _error(
                        f"{path}/value",
                        "a contribution supplies its data through `command` or `value`, not "
                        "both (COR-052 point 2).",
                    )

    return findings


def _component_name(raw: Mapping[Any, Any], expected: str | None, component_dir: Path) -> str:
    """The component's name for a message: as the package declares it, else the
    name its directory gives it."""
    component = raw.get("component")
    name = component.get("name") if isinstance(component, Mapping) else None
    if isinstance(name, str) and name:
        return name
    return expected if expected is not None else component_dir.name


def role_of(address: str) -> str | None:
    """The qualified role of a point address `<publisher>::<role>:<point>`, or None
    when the address is not one (the shape pass reports that). Shared with the
    wiring resolver (`connections`), so one parser reads every address."""
    role, sep, point = address.rpartition(POINT_SEPARATOR)
    if not sep or not point or ROLE_QUALIFIER not in role or role.endswith(POINT_SEPARATOR):
        return None
    return role


def undeclared_command(
    reference: str, command_leaves: Mapping[tuple[str, ...], Mapping[Any, Any]]
) -> str | None:
    """Why `reference` — a path through `commands:`, tokens separated by spaces —
    names no leaf, or None when it does. One check for every command reference:
    an offered event's emitter, a filler, a subscriber, a validator."""
    if resolve_command(command_leaves, reference) is not None:
        return None
    known = sorted(" ".join(t) for t in command_leaves)
    declared = f" (declared: {known})." if known else " (the package declares no commands)."
    return f"command {reference!r} is not declared in `commands:`{declared}"


def _error_appender(findings: list[PackageFinding]) -> Callable[[str, str], None]:
    """An `error(path, message)` that appends an ERROR finding to `findings`."""

    def error(path: str, message: str) -> None:
        findings.append(PackageFinding(path, Severity.ERROR, message))

    return error


def _check_relative(findings: list[PackageFinding], path: str, value: Any, what: str) -> bool:
    """Append an error unless `value` is a relative path with no `..` segment. True when it is."""
    if not isinstance(value, str) or not value:
        return False  # the shape pass reports the type
    problem = relative_path_problem(value)
    if problem is None:
        return True
    findings.append(PackageFinding(path, Severity.ERROR, f"{value!r} is not {what}: it {problem}."))
    return False


def relative_path_problem(value: str) -> str | None:
    """Why `value` is not a plain relative path (absolute, or climbing with `..`); None when it is."""
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
        return "is absolute"
    if ".." in PurePosixPath(value).parts:
        return "contains a `..` segment"
    return None


# --- every installed component --------------------------------------


@dataclass(frozen=True)
class PackagesPass:
    """The `packages` member of `pkit validate`: one report per registered component
    whose `package.yaml` is present, and the note when the tree ships no schema.
    The checks *across* packages are the wiring resolver's — the `connections`
    and `versions` members (`connections.connections_outcome`, `versions_outcome`).
    """

    reports: tuple[PackageReport, ...]
    schema_note: str | None = None  # "no schema present, skipped" (ADR-056 point 1)

    @property
    def errors(self) -> int:
        return sum(len(r.errors) for r in self.reports)

    @property
    def warnings(self) -> int:
        return sum(len(r.warnings) for r in self.reports)


def installed_package_files(target_root: Path) -> list[tuple[str, Path, Path]]:
    """`(name, component_dir, package.yaml)` for every registered capability and adapter
    whose package file is present in the tree, in manifest order."""
    backbone = read_backbone_manifest(target_root)
    if backbone is None:
        return []
    out: list[tuple[str, Path, Path]] = []
    for entry in backbone.components:
        area = _COMPONENT_DIRS.get(entry.kind)
        if area is None:
            continue
        component_dir = target_root / ".pkit" / area / entry.name
        package = component_dir / "package.yaml"
        if package.is_file():
            out.append((entry.name, component_dir, package))
    return out


def load_package_schema(target_root: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    """The tree's package schema, or (None, note) when the tree ships none."""
    try:
        return load_backbone_schema(target_root, SCHEMA_KIND), None
    except BackboneSchemaMissing:
        return None, (
            f"no {SCHEMA_KIND} schema present under .pkit/schemas/backbone/ — shape and "
            "unknown-key checks skipped; repository checks ran."
        )


def validate_installed_packages(target_root: Path) -> PackagesPass:
    """Validate every registered component's package file (the `packages` member)."""
    schema, note = load_package_schema(target_root)
    reports = [
        validate_package_file(package, schema, component_dir=component_dir, expected_name=name)
        for name, component_dir, package in installed_package_files(target_root)
    ]
    return PackagesPass(reports=tuple(reports), schema_note=note)


UMBRELLA_SEVERITY = {
    Severity.ERROR: validators.Severity.ERROR,
    Severity.WARNING: validators.Severity.WARNING,
}


def outcome(target_root: Path) -> validators.Outcome:
    """The `packages` member of `pkit validate`: a count line, the note, every finding."""
    result = validate_installed_packages(target_root)
    summary = [
        f"{len(result.reports)} package file(s) checked; "
        f"{result.errors} error(s), {result.warnings} warning(s)."
    ]
    if result.schema_note:
        summary.append(result.schema_note)
    findings = tuple(
        validators.Finding(
            _locate(target_root, report.file, finding),
            finding.message,
            UMBRELLA_SEVERITY[finding.severity],
        )
        for report in result.reports
        for finding in report.findings
    )
    return validators.Outcome(tuple(summary), findings)


# --- rendering helpers ------------------------------------------------


def _locate(target_root: Path, file: Path, finding: PackageFinding) -> str:
    try:
        rel = file.relative_to(target_root)
    except ValueError:
        rel = file
    return f"{rel}:{finding.path}" if finding.path else str(rel)


def _kind(value: Any) -> str:
    return "null" if value is None else type(value).__name__


def _token(segment: Any) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return str(segment).replace("~", "~0").replace("/", "~1")


def _pointer(path: Iterable[Any]) -> str:
    return "".join(f"/{_token(p)}" for p in path)


def _sort_key(path: Iterable[Any]) -> list[str]:
    return [str(p) for p in path]
