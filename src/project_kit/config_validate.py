"""The backbone configuration pass of `pkit validate` (COR-048 point 4).

The project's declarations to the backbone live in one project-owned file,
`.pkit/project/config.yaml` (COR-048 point 1; `report_context` reads its
`name` key). This module is the *strict* side of COR-048's "strict when
checked, forgiving when read": it validates the whole file against the
backbone-shipped `config.schema.json` (loaded from the project's tree, never
from a copy in the binary — ADR-056 point 1) and then runs the repository
checks the owning records ask for:

- **Shape.** Every JSON Schema violation is a finding; an unknown key is
  rendered by the shared renderer with the nearest known key
  (`backbone_schemas.render_unknown_key`, ADR-056 point 4). An absent or
  empty file is clean — defaults apply (COR-048 point 3); an unparsable one
  is an error.
- **Documentation roots** (COR-049 points 1 and 7): each root resolves, after
  following links, inside the repository and outside `.pkit/` — otherwise an
  error; a root that does not exist yet is a warning.
- **Friction paths** (COR-050 points 12 and 14): each place / surface /
  exclude pattern stays inside the repository — not absolute, not climbing
  above the root, not resolving outside it through a link — otherwise an
  error; a pattern matching nothing is a warning. The patterns are the ones
  discovery reads (`friction_discovery.read_friction_settings`), and a
  pattern matches something when it covers a file of the working tree's one
  listing, by the reading every check applies (`pattern_matches_any`) — so
  what this pass calls live is what the checks see (ADR-057 point 2). This
  pass is the one owner of these findings and of the `friction.mode` enum
  (the schema); the friction pass reads the settings and reports only on the
  artefacts.
- **Connections** (COR-053 point 7, COR-052 point 4): each provider or
  contributor selection names an installed capability, read from the
  backbone manifest — otherwise an error naming the fix. A provider selection
  must name a capability that *provides the role*; a contributor selection
  must name a `single` data point the active provider of its role defines and
  a capability that *contributes to it* — each read from the wiring as
  resolved once per run (`connections.shared_wiring`), each an error naming
  the fix. A role with two installed providers and no selection is the
  resolver's own finding (the `connections` heading), and while a role has no
  active provider a selection of its points is not judged a second time.

Findings are structured records (a JSON Pointer into the file, a severity,
a message) in a deterministic order: shape findings by position, then the
repository checks in a fixed order — docs, friction, connections — each entry
in written order. Only errors fail validation.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import backbone_schemas, validators
from project_kit import connections as wiring
from project_kit.friction_discovery import (
    SettingsPath,
    is_inside_repository,
    pattern_matches_any,
    read_friction_settings,
)
from project_kit.manifest import read_backbone_manifest
from project_kit.project_config import PROJECT_CONFIG_RELPATH, project_config_path
from project_kit.working_tree import working_tree

# The schema kind under `.pkit/schemas/backbone/` (ADR-056 point 1).
CONFIG_SCHEMA_KIND = "config"

# The methodology's own tree, which no documentation root may resolve into
# (COR-049 point 1).
METHODOLOGY_TREE = ".pkit"

# Where the records' repository checks look, by top-level key.
DOCS_KEY = "docs"
FRICTION_KEY = "friction"
FRICTION_PATTERN_KEYS = ("places", "surface", "exclude")
CONNECTIONS_KEY = "connections"
PROVIDERS_KEY = "providers"
SELECTIONS_KEY = "selections"

# What a key of the two pattern-constrained connection maps must look like,
# for the finding when one does not (COR-053 point 2's address forms).
ADDRESS_FORMS = {
    PROVIDERS_KEY: "<publisher>::<role>",
    SELECTIONS_KEY: "<publisher>::<role>:<point>",
}


class Severity(Enum):
    """Whether a finding fails validation, is only reported, or merely informs."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ConfigFinding:
    """One finding on the configuration file.

    `path` is a JSON Pointer into the file from its root (`""` for the file as
    a whole, `/docs/user` for a value).
    """

    path: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class ConfigReport:
    """Outcome of the pass over one project's configuration file."""

    location: str  # the file, relative to the project root
    present: bool  # False when absent or empty: defaults apply, nothing to check
    schema_present: bool  # False when the tree ships no config schema (skipped)
    findings: tuple[ConfigFinding, ...]

    def by_severity(self, severity: Severity) -> tuple[ConfigFinding, ...]:
        return tuple(f for f in self.findings if f.severity is severity)

    @property
    def errors(self) -> tuple[ConfigFinding, ...]:
        return self.by_severity(Severity.ERROR)

    @property
    def is_clean(self) -> bool:
        """No errors. Warnings and information never fail validation."""
        return not self.errors


def run_configuration_pass(target_root: Path) -> ConfigReport:
    """Validate the project's configuration file; never raises on its content."""
    location = PROJECT_CONFIG_RELPATH.as_posix()
    path = project_config_path(target_root)

    try:
        schema = backbone_schemas.load_backbone_schema(target_root, CONFIG_SCHEMA_KIND)
    except backbone_schemas.BackboneSchemaMissing:
        # A tree recorded before the schema landed: skip, never substitute
        # the binary's idea of the shape (ADR-056 point 1).
        return ConfigReport(
            location=location, present=path.is_file(), schema_present=False, findings=()
        )
    except backbone_schemas.BackboneSchemaInvalid as exc:
        # The load-check of `pkit schemas validate` owns the detailed report;
        # here it only means the file cannot be checked.
        return ConfigReport(
            location=location,
            present=path.is_file(),
            schema_present=True,
            findings=(ConfigFinding("", Severity.ERROR, f"cannot validate: {exc}"),),
        )

    if not path.is_file():
        return ConfigReport(location=location, present=False, schema_present=True, findings=())

    data, parse_error = _load_yaml(path)
    if parse_error is not None:
        return ConfigReport(
            location=location,
            present=True,
            schema_present=True,
            findings=(ConfigFinding("", Severity.ERROR, parse_error),),
        )
    if data is None:
        # An empty file: defaults apply (COR-048 point 3).
        return ConfigReport(location=location, present=False, schema_present=True, findings=())
    if not isinstance(data, Mapping):
        return ConfigReport(
            location=location,
            present=True,
            schema_present=True,
            findings=(
                ConfigFinding(
                    "",
                    Severity.ERROR,
                    f"the file must be a mapping of keys to values, not {_type_name(data)}.",
                ),
            ),
        )

    config = _string_keys(data)
    findings = _shape_findings(config, schema)
    # A value the shape pass refused is not checked again against the
    # repository: one finding per mistake.
    flagged = frozenset(f.path for f in findings)
    findings.extend(_docs_findings(target_root, config.get(DOCS_KEY), flagged))
    findings.extend(_friction_findings(target_root, config.get(FRICTION_KEY), flagged))
    findings.extend(_connections_findings(target_root, config.get(CONNECTIONS_KEY), flagged))
    return ConfigReport(
        location=location, present=True, schema_present=True, findings=tuple(findings)
    )


# --- shape -------------------------------------------------------------------


def _shape_findings(config: Mapping[str, Any], schema: Mapping[str, Any]) -> list[ConfigFinding]:
    """The JSON Schema pass, with every unknown key rendered by the shared renderer.

    Sorted by position, then message, so the order never depends on the
    validator's traversal.
    """
    registry = Registry().with_resource(
        uri=schema.get("$id", f"{CONFIG_SCHEMA_KIND}.schema.json"),
        resource=Resource.from_contents(schema, default_specification=DRAFT202012),
    )
    validator = Draft202012Validator(schema, registry=registry)
    findings: list[ConfigFinding] = []
    for error in validator.iter_errors(config):
        findings.extend(_render_schema_error(error))
    return sorted(findings, key=lambda f: (f.path, f.message))


def _render_schema_error(error: ValidationError) -> list[ConfigFinding]:
    """One finding per violation; an `additionalProperties` error becomes one per unknown key."""
    pointer = _pointer(error.absolute_path)
    unknown = backbone_schemas.unknown_keys(error)
    if not unknown:
        return [ConfigFinding(pointer, Severity.ERROR, error.message)]

    known = tuple((error.schema.get("properties") or {}).keys())
    findings: list[ConfigFinding] = []
    for key in unknown:
        key_pointer = f"{pointer}/{_pointer_token(key)}"
        if known:
            message = backbone_schemas.render_unknown_key(key, known)
        else:
            # A pattern-keyed map (the two connection maps): there is no
            # known set to suggest from, only the address form the key must take.
            form = ADDRESS_FORMS.get(_last_segment(pointer), "the address form")
            message = f"key {key!r} is not a {form} address."
        findings.append(ConfigFinding(key_pointer, Severity.ERROR, message))
    return findings


def _docs_findings(target_root: Path, docs: Any, flagged: frozenset[str]) -> list[ConfigFinding]:
    if not isinstance(docs, Mapping):
        return []
    findings: list[ConfigFinding] = []
    for audience, value in docs.items():
        pointer = f"/{DOCS_KEY}/{audience}"
        if pointer in flagged or not isinstance(value, str) or not value:
            continue  # the shape pass already reported it
        findings.extend(_root_findings(target_root, pointer, value))
    return findings


def _root_findings(target_root: Path, pointer: str, value: str) -> list[ConfigFinding]:
    """One root: inside the repository and outside `.pkit/` after following links (error);
    not existing yet (warning)."""
    repo = target_root.resolve()
    candidate = target_root / value
    resolved = candidate.resolve()
    if not resolved.is_relative_to(repo):
        return [
            ConfigFinding(
                pointer,
                Severity.ERROR,
                f"documentation root {value!r} resolves to {resolved}, outside the repository; "
                f"a root must lie inside it (COR-049 point 1).",
            )
        ]
    if resolved == repo / METHODOLOGY_TREE or resolved.is_relative_to(repo / METHODOLOGY_TREE):
        return [
            ConfigFinding(
                pointer,
                Severity.ERROR,
                f"documentation root {value!r} resolves inside the methodology's own tree "
                f"({METHODOLOGY_TREE}/); a root must lie outside it (COR-049 point 1).",
            )
        ]
    if not resolved.is_dir():
        what = "is not a directory" if resolved.exists() else "does not exist yet"
        return [
            ConfigFinding(
                pointer,
                Severity.WARNING,
                f"documentation root {value!r} {what}; the default applies to readers "
                f"until it is created (COR-049 point 7).",
            )
        ]
    return []


# --- friction paths (COR-050) -----------------------------------------------


def _friction_findings(
    target_root: Path, friction: Any, flagged: frozenset[str]
) -> list[ConfigFinding]:
    """The project's patterns as discovery reads them, each judged where it is written.

    A key whose value is not a list was refused whole by the shape pass, and a
    pattern the shape pass refused is not judged again: one finding per mistake.
    """
    if not isinstance(friction, Mapping):
        return []
    settings = read_friction_settings(target_root)
    listing = functools.cache(lambda: working_tree(target_root).files())  # on first need
    findings: list[ConfigFinding] = []
    for key in FRICTION_PATTERN_KEYS:
        if not isinstance(friction.get(key), list):
            continue  # the shape pass already reported it
        declared: tuple[SettingsPath, ...] = getattr(settings, key)
        for setting in declared:
            if setting.is_capability or setting.pointer in flagged:
                continue  # a capability's is the packages pass's; a refused one is reported
            findings.extend(_pattern_findings(target_root, setting, listing))
    return findings


def _pattern_findings(
    target_root: Path, setting: SettingsPath, listing: Callable[[], Sequence[str]]
) -> list[ConfigFinding]:
    """One path or glob: stays inside the repository (error otherwise); matches
    something (warning otherwise).

    Both are discovery's answers. Inside is judged on the text, and on where
    the literal prefix resolves after following links (`is_inside_repository`);
    matching is over the working tree's one listing, by the reading every
    check applies (`pattern_matches_any`).
    """
    pattern = setting.value
    if not is_inside_repository(target_root, pattern):
        return [
            ConfigFinding(
                setting.pointer,
                Severity.ERROR,
                f"friction pattern {pattern!r} leaves the repository (absolute, climbing above "
                f"the root, or resolving outside it through a link); every path in these "
                f"settings stays inside it (COR-050 point 14).",
            )
        ]
    if not pattern_matches_any(pattern, listing()):
        return [
            ConfigFinding(
                setting.pointer,
                Severity.WARNING,
                f"friction pattern {pattern!r} matches nothing in the repository; a dead "
                f"pattern keeps silence looking like health (COR-050 point 12).",
            )
        ]
    return []


# --- connections (COR-053, COR-052) ------------------------------------------


def _connections_findings(
    target_root: Path, connections: Any, flagged: frozenset[str]
) -> list[ConfigFinding]:
    if not isinstance(connections, Mapping):
        return []
    installed = _installed_capabilities(target_root)
    # The wiring as resolved once per run, taken when an entry names an installed capability.
    resolved = functools.cache(lambda: wiring.shared_wiring(target_root))
    findings: list[ConfigFinding] = []
    for key in (PROVIDERS_KEY, SELECTIONS_KEY):
        entries = connections.get(key)
        if not isinstance(entries, Mapping):
            continue
        for address, capability in entries.items():
            pointer = f"/{CONNECTIONS_KEY}/{key}/{_pointer_token(address)}"
            if pointer in flagged or not isinstance(capability, str) or not capability:
                continue  # the shape pass already reported it
            if capability not in installed:
                findings.append(
                    ConfigFinding(
                        pointer,
                        Severity.ERROR,
                        f"{capability!r} is not an installed capability; install it "
                        f"(`pkit capabilities install {capability}`) or remove the entry "
                        f"(COR-048 point 2).",
                    )
                )
                continue
            if key == PROVIDERS_KEY:
                problem = _provider_problem(resolved().declarations, str(address), capability)
            else:
                problem = _selection_problem(resolved(), str(address), capability)
            if problem is not None:
                findings.append(ConfigFinding(pointer, Severity.ERROR, problem))
    return findings


def _installed_capabilities(target_root: Path) -> frozenset[str]:
    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        return frozenset()
    return frozenset(entry.name for entry in manifest.components if entry.kind == "capability")


def _provider_problem(declarations: wiring.Declarations, role: str, capability: str) -> str | None:
    """The provider-selection key names a capability that provides the role (COR-053 point 7)."""
    providers = declarations.providers_of(role)
    if capability in providers:
        return None
    roles = declarations.roles_of(capability)
    provides = f"it provides {_names(roles)}" if roles else "it provides no role"
    choice = (
        f"the installed providers of the role are {_names(providers)}; select one of them"
        if providers
        else "no installed capability provides the role; install one"
    )
    return (
        f"{capability!r} does not provide role {role!r} ({provides}); {choice}, or remove "
        f"the entry (COR-053 point 7)."
    )


def _selection_problem(resolved: wiring.Wiring, address: str, capability: str) -> str | None:
    """The contributor-selection key names a `single` data point and one of its
    installed contributors (COR-052 point 4), as the resolved wiring defines them:
    the point of the active provider of its role (COR-053 point 1)."""
    point = resolved.data_point(address)
    if point is None:
        return _undefined_point_problem(resolved, address)
    if point.point.combination != "single":
        declared = point.point.combination or "no combination"
        return (
            f"point {address!r} is not a `single` point (declared: {declared}); a contributor "
            f"selection applies only to `single` points — remove the entry (COR-052 point 4)."
        )
    contributors = point.contributors
    if capability in contributors:
        return None
    known = (
        f"its installed contributors are {_names(contributors)}; select one of them"
        if contributors
        else "no installed capability contributes to it"
    )
    return (
        f"{capability!r} declares no contribution to {address!r}; {known}, or remove the "
        f"entry (COR-052 point 4)."
    )


def _undefined_point_problem(resolved: wiring.Wiring, address: str) -> str | None:
    """Why no data point is defined at `address`, or None when another finding says it.

    While the role has no active provider — two providers and no selection, or
    a provider selection naming no provider — that is the finding, and which
    points exist is not known until it is fixed. A point only a provider that
    is not the active one declares is not defined in the project.
    """
    points = [
        p
        for p in resolved.declarations.points
        if p.address == address and p.kind is wiring.PointKind.DATA
    ]
    if not points:
        return (
            f"no installed capability defines a data point {address!r}; correct the address "
            f"or remove the entry (COR-052 point 4)."
        )
    role = points[0].role
    binding = resolved.role(role)
    if binding is None or binding.active is None:
        return None  # the role conflict, or the provider selection, is the finding
    declared = sorted({p.provider for p in points})
    return (
        f"{binding.active!r}, the active provider of role {role!r}, defines no data point "
        f"{address!r} — only {_names(declared)} declare it, whose points are not defined in "
        f"this project (COR-053 point 1); correct the address or remove the entry "
        f"(COR-052 point 4)."
    )


def _names(names: Iterable[str]) -> str:
    return ", ".join(repr(n) for n in names)


# --- rendering ---------------------------------------------------------------


UMBRELLA_SEVERITY = {
    Severity.ERROR: validators.Severity.ERROR,
    Severity.WARNING: validators.Severity.WARNING,
    Severity.INFO: validators.Severity.INFO,
}


def outcome(target_root: Path) -> validators.Outcome:
    """The `configuration` member of `pkit validate`: the file's state, then every finding."""
    return as_outcome(run_configuration_pass(target_root))


def as_outcome(report: ConfigReport) -> validators.Outcome:
    """The pass's report as the umbrella's outcome: one state line naming the file,
    then each finding located by JSON Pointer into it, at its own severity."""
    if not report.schema_present:
        state = "no config schema present in this tree; skipped."
    elif not report.present and not report.findings:
        state = "absent or empty: defaults apply."
    elif not report.findings:
        state = "valid."
    else:
        state = ", ".join(
            f"{len(report.by_severity(sev))} {sev.value}"
            for sev in Severity
            if report.by_severity(sev)
        ) + "."
    findings = tuple(
        validators.Finding(
            f"{report.location}:{finding.path}" if finding.path else report.location,
            finding.message,
            UMBRELLA_SEVERITY[finding.severity],
        )
        for finding in report.findings
    )
    return validators.Outcome((f"{report.location}: {state}",), findings)


# --- helpers -----------------------------------------------------------------


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    """Parse the file. Returns (data, None) or (None, reason)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"unreadable: {exc}."
    try:
        return YAML(typ="safe").load(text), None
    except YAMLError as exc:
        return None, f"does not parse as YAML: {str(exc).splitlines()[0]}"


def _string_keys(obj: Any) -> Any:
    """Every mapping key as text, recursively — JSON Schema and the renderer know only text keys."""
    if isinstance(obj, Mapping):
        return {str(k): _string_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_string_keys(x) for x in obj]
    return obj


def _type_name(value: Any) -> str:
    if isinstance(value, list):
        return "a list"
    if isinstance(value, str):
        return "a bare string"
    return f"a {type(value).__name__}"


def _pointer(segments: Iterable[Any]) -> str:
    parts = [_pointer_token(s) for s in segments]
    return "/" + "/".join(parts) if parts else ""


def _pointer_token(segment: Any) -> str:
    """One JSON Pointer reference token (RFC 6901 escaping)."""
    return str(segment).replace("~", "~0").replace("/", "~1")


def _last_segment(pointer: str) -> str:
    return pointer.rsplit("/", 1)[-1] if pointer else ""
